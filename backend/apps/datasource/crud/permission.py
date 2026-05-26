import json
from typing import List, Optional

from sqlalchemy import and_
from sqlbot_xpack.permissions.api.permission import transRecord2DTO
from sqlbot_xpack.permissions.models.ds_permission import DsPermission, PermissionDTO
from sqlbot_xpack.permissions.models.ds_rules import DsRules

from apps.datasource.crud.row_permission import transFilterTree
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from common.core.deps import CurrentUser, SessionDep


def match_rule(rule: DsRules, current_user: CurrentUser, permission_id: int) -> bool:
    """Check if a rule matches the current user for a given permission.
    
    A rule matches when:
    1. The permission_id is in the rule's permission_list, AND
    2. Any of the following is true (OR semantics):
       - current_user.id is in rule.user_list
       - Any of current_user.role_ids intersects with rule.role_list
       - Any of current_user.dept_ids intersects with rule.dept_list
    """
    p_list = json.loads(rule.permission_list) if rule.permission_list else []
    if p_list is None or permission_id not in p_list:
        return False

    # Check user_list (backward compatible)
    u_list = json.loads(rule.user_list) if rule.user_list else []
    if u_list and (current_user.id in u_list or f'{current_user.id}' in u_list):
        return True

    # Check role_list (use getattr for xpack compatibility)
    role_list_raw = getattr(rule, 'role_list', None)
    r_list = json.loads(role_list_raw) if role_list_raw else []
    if r_list:
        user_role_ids = getattr(current_user, 'role_ids', None) or []
        if any(rid in user_role_ids for rid in r_list):
            return True

    # Check dept_list (use getattr for xpack compatibility)
    dept_list_raw = getattr(rule, 'dept_list', None)
    d_list = json.loads(dept_list_raw) if dept_list_raw else []
    if d_list:
        user_dept_ids = getattr(current_user, 'dept_ids', None) or []
        if any(did in user_dept_ids for did in d_list):
            return True

    return False


def get_row_permission_filters(session: SessionDep, current_user: CurrentUser, ds: CoreDatasource,
                               tables: Optional[list] = None, single_table: Optional[CoreTable] = None):
    if single_table:
        table_list = [session.get(CoreTable, single_table.id)]
    else:
        table_list = session.query(CoreTable).filter(
            and_(CoreTable.ds_id == ds.id, CoreTable.table_name.in_(tables))
        ).all()

    filters = []
    if is_normal_user(current_user):
        contain_rules = session.query(DsRules).all()
        for table in table_list:
            row_permissions = session.query(DsPermission).filter(
                and_(DsPermission.table_id == table.id, DsPermission.type == 'row')).all()
            res: List[PermissionDTO] = []
            if row_permissions is not None:
                for permission in row_permissions:
                    # check permission and user in same rules (with role/dept support)
                    flag = False
                    for r in contain_rules:
                        if match_rule(r, current_user, permission.id):
                            flag = True
                            break
                    if flag:
                        res.append(transRecord2DTO(session, permission))
            where_str = transFilterTree(session, current_user, res, ds)
            if where_str:
                filters.append({"table": table.table_name, "filter": where_str})
    return filters


def get_column_permission_fields(session: SessionDep, current_user: CurrentUser, table: CoreTable,
                                 fields: list[CoreField], contain_rules: list[DsRules]):
    if is_normal_user(current_user):
        column_permissions = session.query(DsPermission).filter(
            and_(DsPermission.table_id == table.id, DsPermission.type == 'column')).all()
        if column_permissions is not None:
            for permission in column_permissions:
                # check permission and user in same rules (with role/dept support)
                flag = False
                for r in contain_rules:
                    if match_rule(r, current_user, permission.id):
                        flag = True
                        break
                if flag:
                    permission_list = json.loads(permission.permissions)
                    fields = filter_list(fields, permission_list)
    return fields


def is_normal_user(current_user: CurrentUser):
    return current_user.id != 1


def filter_list(list_a, list_b):
    id_to_invalid = {}
    for b in list_b:
        if not b['enable']:
            id_to_invalid[b['field_id']] = True

    return [a for a in list_a if not id_to_invalid.get(a.id, False)]
