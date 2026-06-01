"""
Cleanup Duplicate Users Script

This script identifies and removes duplicate user accounts from the database.
For each duplicate account, it keeps the most recently created user and removes the rest.

WARNING: This script performs DELETE operations. Please backup your database before running.
"""

from common.core.db import engine
from apps.system.models.user import UserModel
from apps.system.models.system_model import UserWsModel
from sqlmodel import Session, select, func
import sys

def find_duplicate_accounts(session: Session):
    """Find all accounts that have more than one user record."""
    stmt = (
        select(UserModel.account, func.count(UserModel.id).label('count'))
        .group_by(UserModel.account)
        .having(func.count(UserModel.id) > 1)
    )
    return session.exec(stmt).all()

def get_users_by_account(session: Session, account: str):
    """Get all users with the given account, ordered by create_time DESC."""
    stmt = (
        select(UserModel)
        .where(UserModel.account == account)
        .order_by(UserModel.create_time.desc())
    )
    return session.exec(stmt).all()

def delete_user_and_related(session: Session, user_id: int):
    """Delete a user and their related workspace mappings."""
    # Delete workspace mappings first
    ws_stmt = select(UserWsModel).where(UserWsModel.uid == user_id)
    ws_mappings = session.exec(ws_stmt).all()
    
    for ws_mapping in ws_mappings:
        session.delete(ws_mapping)
        print(f"    - Deleted workspace mapping (uid={user_id}, oid={ws_mapping.oid})")
    
    # Delete the user
    user_stmt = select(UserModel).where(UserModel.id == user_id)
    user = session.exec(user_stmt).first()
    if user:
        session.delete(user)
        print(f"    - Deleted user (id={user_id}, account={user.account})")

def cleanup_duplicates(dry_run: bool = True):
    """Main cleanup function."""
    print("=" * 80)
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
    else:
        print("LIVE MODE - Changes WILL be made to the database")
    print("=" * 80)
    
    with Session(engine) as session:
        duplicates = find_duplicate_accounts(session)
        
        if not duplicates:
            print("\nNo duplicate accounts found!")
            return
        
        print(f"\nFound {len(duplicates)} accounts with duplicates:\n")
        
        total_to_delete = 0
        
        for account, count in duplicates:
            print(f"Account: '{account}' ({count} records)")
            users = get_users_by_account(session, account)
            
            # Keep the first one (most recent), delete the rest
            keep_user = users[0]
            users_to_delete = users[1:]
            
            print(f"  ✓ KEEP: id={keep_user.id}, create_time={keep_user.create_time}")
            
            for user in users_to_delete:
                print(f"  ✗ DELETE: id={user.id}, create_time={user.create_time}")
                total_to_delete += 1
            
            print()
        
        print(f"Total users to delete: {total_to_delete}")
        print()
        
        if dry_run:
            print("To execute the cleanup, run:")
            print("  python scripts/cleanup_duplicate_users.py --execute")
            return
        
        # Confirm before deletion
        confirm = input("Are you sure you want to delete these users? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
        
        # Perform deletion
        deleted_count = 0
        for account, count in duplicates:
            users = get_users_by_account(session, account)
            users_to_delete = users[1:]
            
            for user in users_to_delete:
                try:
                    delete_user_and_related(session, user.id)
                    deleted_count += 1
                except Exception as e:
                    print(f"    ✗ ERROR deleting user {user.id}: {e}")
        
        session.commit()
        print(f"\n✓ Successfully deleted {deleted_count} duplicate users")
        print("=" * 80)

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    cleanup_duplicates(dry_run=dry_run)
