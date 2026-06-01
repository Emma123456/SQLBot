"""
Delete Users from Specific Workspace Script

This script deletes all users (and related records) from a specific workspace.
It safely removes:
1. User workspace mappings (sys_user_ws)
2. User platform mappings (sys_user_platform)  
3. User records (sys_user)

WARNING: This script performs DELETE operations. Please backup your database before running.
"""

from common.core.db import engine
from apps.system.models.user import UserModel, UserPlatformModel
from apps.system.models.system_model import UserWsModel, WorkspaceModel
from sqlmodel import Session, select
import sys

def get_workspace_by_oid(session: Session, oid: int):
    """Get workspace by OID."""
    stmt = select(WorkspaceModel).where(WorkspaceModel.id == oid)
    return session.exec(stmt).first()

def get_users_in_workspace(session: Session, oid: int):
    """Get all users in a specific workspace."""
    stmt = (
        select(UserModel)
        .join(UserWsModel, UserModel.id == UserWsModel.uid)
        .where(UserWsModel.oid == oid)
    )
    return session.exec(stmt).all()

def delete_user_completely(session: Session, user_id: int):
    """Delete a user and all related records."""
    # 1. Delete workspace mappings
    ws_stmt = select(UserWsModel).where(UserWsModel.uid == user_id)
    ws_mappings = session.exec(ws_stmt).all()
    ws_count = 0
    for ws_mapping in ws_mappings:
        session.delete(ws_mapping)
        ws_count += 1
    
    # 2. Delete platform mappings
    platform_stmt = select(UserPlatformModel).where(UserPlatformModel.uid == user_id)
    platform_mappings = session.exec(platform_stmt).all()
    platform_count = 0
    for platform_mapping in platform_mappings:
        session.delete(platform_mapping)
        platform_count += 1
    
    # 3. Delete the user
    user_stmt = select(UserModel).where(UserModel.id == user_id)
    user = session.exec(user_stmt).first()
    if user:
        session.delete(user)
    
    return ws_count, platform_count

def delete_workspace_users(oid: int, dry_run: bool = True):
    """Main deletion function."""
    print("=" * 80)
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
    else:
        print("LIVE MODE - Changes WILL be made to the database")
    print("=" * 80)
    
    with Session(engine) as session:
        # Get workspace info
        workspace = get_workspace_by_oid(session, oid)
        if not workspace:
            print(f"\n✗ Workspace with oid={oid} not found!")
            return
        
        print(f"\nWorkspace: {workspace.name}")
        print(f"OID: {oid}\n")
        
        # Get users in workspace
        users = get_users_in_workspace(session, oid)
        
        if not users:
            print("No users found in this workspace.")
            return
        
        print(f"Found {len(users)} users to delete:\n")
        
        for i, user in enumerate(users, 1):
            print(f"  {i}. id={user.id}, account={user.account}, name={user.name}, origin={user.origin}")
        
        print(f"\nTotal users to delete: {len(users)}")
        print()
        
        if dry_run:
            print("To execute the deletion, run:")
            print(f"  python scripts/delete_workspace_users.py --oid {oid} --execute")
            return
        
        # Confirm before deletion
        print("⚠️  WARNING: This will permanently delete:")
        print(f"   - {len(users)} user records")
        print(f"   - Related workspace mappings (sys_user_ws)")
        print(f"   - Related platform mappings (sys_user_platform)")
        print()
        
        confirm = input("Are you sure you want to delete these users? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
        
        # Perform deletion
        deleted_users = 0
        deleted_ws = 0
        deleted_platforms = 0
        
        for user in users:
            try:
                ws_count, platform_count = delete_user_completely(session, user.id)
                deleted_users += 1
                deleted_ws += ws_count
                deleted_platforms += platform_count
                print(f"✓ Deleted user: {user.account} (id={user.id})")
            except Exception as e:
                print(f"✗ ERROR deleting user {user.id} ({user.account}): {e}")
        
        session.commit()
        
        print(f"\n{'=' * 80}")
        print(f"✓ Deletion completed successfully!")
        print(f"  - Users deleted: {deleted_users}")
        print(f"  - Workspace mappings deleted: {deleted_ws}")
        print(f"  - Platform mappings deleted: {deleted_platforms}")
        print(f"{'=' * 80}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Delete users from a specific workspace')
    parser.add_argument('--oid', type=int, required=True, help='Workspace OID')
    parser.add_argument('--execute', action='store_true', help='Execute deletion (default is dry-run)')
    
    args = parser.parse_args()
    
    delete_workspace_users(oid=args.oid, dry_run=not args.execute)
