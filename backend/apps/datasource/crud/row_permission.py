# Author: Junjun
# Date: 2025/6/25

from typing import List, Dict

from apps.datasource.models.datasource import CoreField, CoreDatasource
from apps.db.constant import DB
from apps.system.models.system_variable_model import SystemVariable
from common.core.deps import SessionDep, CurrentUser


def transFilterTree(session: SessionDep, current_user: CurrentUser, tree_list: List[any],
                    ds: CoreDatasource) -> str | None:
    if tree_list is None:
        return None
    res: List[str] = []
    for dto in tree_list:
        tree = dto.tree
        if tree is None:
            continue
        tree_exp = transTreeToWhere(session, current_user, tree, ds)
        if tree_exp is not None:
            res.append(tree_exp)
    return " AND ".join(res)


def transTreeToWhere(session: SessionDep, current_user: CurrentUser, tree: any, ds: CoreDatasource) -> str | None:
    if tree is None:
        return None
    logic = tree['logic']

    items = tree['items']
    list: List[str] = []
    if items is not None:
        for item in items:
            exp: str = None
            if item['type'] == 'item':
                exp = transTreeItem(session, current_user, item, ds)
            elif item['type'] == 'tree':
                exp = transTreeToWhere(session, current_user, item['sub_tree'], ds)

            if exp is not None:
                list.append(exp)
    return '(' + f' {logic} '.join(list) + ')' if len(list) > 0 else None


def transTreeItem(session: SessionDep, current_user: CurrentUser, item: Dict, ds: CoreDatasource) -> str | None:
    res: str = None
    field = session.query(CoreField).filter(CoreField.id == int(item['field_id'])).first()
    if field is None:
        return None

    db = DB.get_db(ds.type)
    whereName = db.prefix + field.field_name + db.suffix
    whereTerm = transFilterTerm(item['term'])

    if item['filter_type'] == 'enum':
        if len(item['enum_value']) > 0:
            if ds['type'] == 'sqlServer' and (
                    field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                res = "(" + whereName + " IN (N'" + "',N'".join(item['enum_value']) + "'))"
            else:
                res = "(" + whereName + " IN ('" + "','".join(item['enum_value']) + "'))"
    else:
        # if system variable, do check and get value
        # new field: value_type(variable or normal), variable_id
        value_type = item.get('value_type')
        if value_type and value_type == 'variable':
            # get system variable
            variable_id = item.get('variable_id')
            if variable_id is not None:
                sys_variable = session.query(SystemVariable).filter(SystemVariable.id == variable_id).first()
                if sys_variable is None:
                    return None

                # do inner system variable
                if sys_variable.type == 'system':
                    sys_val = getSysVariableValue(sys_variable, current_user, ds, field, item)
                    if sys_val is None:
                        return None
                    res = whereName + whereTerm + sys_val
                else:
                    # user_attr: value comes from user's extended attributes, no binding needed
                    if getattr(sys_variable, 'value_type', None) == 'user_attr':
                        if sys_variable.var_type == 'list':
                            # list + user_attr: split comma-separated value
                            key = sys_variable.value[0]
                            user_sys_vars = current_user.system_variables or []
                            raw = next((x.get('value') for x in user_sys_vars if x.get('key') == key), None)
                            if not raw:
                                return None
                            values = [v.strip() for v in str(raw).split(',') if v.strip()]
                            if not values:
                                return None
                            is_nvarchar = ds.type == 'sqlServer' and field.field_type.lower() in ('nchar', 'nvarchar')
                            q = "N'" if is_nvarchar else "'"
                            match_mode = getattr(sys_variable, 'match_mode', 'in') or 'in'
                            if match_mode == 'like':
                                # each value as a LIKE clause, joined with OR
                                like_clauses = [f"{whereName} LIKE {q}%{v}%'" for v in values]
                                res = "(" + " OR ".join(like_clauses) + ")"
                            else:
                                whereValue = "(" + ", ".join(f"{q}{v}'" for v in values) + ")"
                                res = whereName + " IN " + whereValue
                        else:
                            sys_val = getSysVariableValue(sys_variable, current_user, ds, field, item)
                            if sys_val is None:
                                return None
                            res = whereName + whereTerm + sys_val
                    else:
                        # check user variable
                        user_variables = current_user.system_variables
                        if user_variables is None or len(user_variables) == 0 or not userHaveVariable(user_variables,
                                                                                                      sys_variable):
                            return None

                        # get user variable
                        u_variable = None
                        for u in user_variables:
                            if u.get('variableId') == sys_variable.id:
                                u_variable = u
                                break
                        if u_variable is None:
                            return None

                        # check value
                        values = u_variable.get('variableValues')
                        if sys_variable.var_type == 'list':
                            # list type: filter against candidate set, force IN clause
                            set_sys = set(sys_variable.value)
                            values = [x for x in (values or []) if x in set_sys]
                            if not values:
                                return None
                            is_nvarchar = ds.type == 'sqlServer' and field.field_type.lower() in ('nchar', 'nvarchar')
                            q = "N'" if is_nvarchar else "'"
                            whereValue = "(" + ", ".join(f"{q}{v}'" for v in values) + ")"
                            res = whereName + " IN " + whereValue
                            return res
                        elif sys_variable.var_type == 'text':
                            set_sys = set(sys_variable.value)
                            values = [x for x in values if x in set_sys]
                            if values is None or len(values) == 0:
                                return None
                        elif sys_variable.var_type == 'number':
                            if (sys_variable.value[0] is not None and values[0] < sys_variable.value[0]) or (
                                    sys_variable.value[1] is not None and values[0] > sys_variable.value[1]):
                                return None
                        elif sys_variable.var_type == 'datetime':
                            if (sys_variable.value[0] is not None and values[0] < sys_variable.value[0]) or (
                                    sys_variable.value[1] is not None and values[0] > sys_variable.value[1]):
                                return None

                        # build exp
                        whereValue = ''
                        if item['term'] == 'null':
                            whereValue = ''
                        elif item['term'] == 'not_null':
                            whereValue = ''
                        elif item['term'] == 'empty':
                            whereValue = "''"
                        elif item['term'] == 'not_empty':
                            whereValue = "''"
                        elif item['term'] == 'in' or item['term'] == 'not in':
                            if ds.type == 'sqlServer' and (
                                    field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                                whereValue = "(N'" + "', N'".join(values) + "')"
                            else:
                                whereValue = "('" + "', '".join(values) + "')"
                        elif item['term'] == 'like' or item['term'] == 'not like':
                            if ds.type == 'sqlServer' and (
                                    field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                                whereValue = f"N'%{values[0]}%'"
                            else:
                                whereValue = f"'%{values[0]}%'"
                        else:
                            if ds.type == 'sqlServer' and (
                                    field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                                whereValue = f"N'{values[0]}'"
                            else:
                                whereValue = f"'{values[0]}'"

                        res = whereName + whereTerm + whereValue
            else:
                return None
        else:
            value = item['value']
            whereValue = ''

            if item['term'] == 'null':
                whereValue = ''
            elif item['term'] == 'not_null':
                whereValue = ''
            elif item['term'] == 'empty':
                whereValue = "''"
            elif item['term'] == 'not_empty':
                whereValue = "''"
            elif item['term'] == 'in' or item['term'] == 'not in':
                if ds.type == 'sqlServer' and (
                        field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                    whereValue = "(N'" + "', N'".join(value.split(",")) + "')"
                else:
                    whereValue = "('" + "', '".join(value.split(",")) + "')"
            elif item['term'] == 'like' or item['term'] == 'not like':
                if ds.type == 'sqlServer' and (
                        field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                    whereValue = f"N'%{value}%'"
                else:
                    whereValue = f"'%{value}%'"
            else:
                if ds.type == 'sqlServer' and (
                        field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
                    whereValue = f"N'{value}'"
                else:
                    whereValue = f"'{value}'"

            res = whereName + whereTerm + whereValue
    return res


def transFilterTerm(term: str) -> str:
    if term == "eq":
        return " = "
    if term == "not_eq":
        return " <> "
    if term == "lt":
        return " < "
    if term == "le":
        return " <= "
    if term == "gt":
        return " > "
    if term == "ge":
        return " >= "
    if term == "in":
        return " IN "
    if term == "not in":
        return " NOT IN "
    if term == "like":
        return " LIKE "
    if term == "not like":
        return " NOT LIKE "
    if term == "null":
        return " IS NULL "
    if term == "not_null":
        return " IS NOT NULL "
    if term == "empty":
        return " = "
    if term == "not_empty":
        return " <> "
    if term == "between":
        return " BETWEEN "
    return ""


def userHaveVariable(user_variables: List, sys_variable: SystemVariable):
    for u in user_variables:
        if sys_variable.id == u.get('variableId'):
            return True
    return False


def getSysVariableValue(sys_variable: SystemVariable, current_user: CurrentUser, ds: CoreDatasource, field: CoreField,
                        item: Dict, ):
    v = None
    if getattr(sys_variable, 'value_type', None) == 'user_attr':
        key = sys_variable.value[0]
        user_sys_vars = current_user.system_variables or []
        v = next((x.get('value') for x in user_sys_vars if x.get('key') == key), None)
    elif sys_variable.value[0] == 'name':
        v = current_user.name
    elif sys_variable.value[0] == 'account':
        v = current_user.account
    elif sys_variable.value[0] == 'email':
        v = current_user.email

    if v is None:
        return None

    whereValue = ''
    if item['term'] == 'null':
        whereValue = ''
    elif item['term'] == 'not_null':
        whereValue = ''
    elif item['term'] == 'empty':
        whereValue = "''"
    elif item['term'] == 'not_empty':
        whereValue = "''"
    elif item['term'] == 'in' or item['term'] == 'not in':
        if ds.type == 'sqlServer' and (
                field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
            whereValue = f"(N'{v}')"
        else:
            whereValue = f"('{v}')"
    elif item['term'] == 'like' or item['term'] == 'not like':
        if ds.type == 'sqlServer' and (
                field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
            whereValue = f"N'%{v}%'"
        else:
            whereValue = f"'%{v}%'"
    else:
        if ds.type == 'sqlServer' and (
                field.field_type == 'nchar' or field.field_type == 'NCHAR' or field.field_type == 'nvarchar' or field.field_type == 'NVARCHAR'):
            whereValue = f"N'{v}'"
        else:
            whereValue = f"'{v}'"

    return whereValue
