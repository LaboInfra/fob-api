from datetime import datetime
from sqlmodel import select

from fob_api.auth import hash_password
from fob_api.models.database import User, UserPasswordReset

class UserManager():
    
    session = None

    def __init__(self, session):
        """
        Initialize the UserManager with a database session.
        """
        self.session = session

    def list_users(self) -> list[User]:
        """
        List all users in the database.
        """
        return self.session.exec(select(User)).all()

    def get_user_by_name(self, username: str) -> User | None:
        """
        Get a user by their username.
        :param username: The username of the user to retrieve.
        :return: The User object if found, None otherwise.
        """
        return self.session.exec(select(User).where(User.username == username)).first()

    def delete_user(self, user: User) -> bool:
        """
        Delete a user from the database.
        :param user: The User object to delete.
        :return: True if the user was deleted, raise an exception otherwise.
        :raises NotImplementedError: This method is not implemented yet.
        :future-raise: FobApiCantDeleteUserException: If the user cannot be deleted.
        """
        # todo implement check for
        # - purge user on vpn
        # - purge openstack project
        # - purge quota
        # - purge user from openstack
        # - delete user from db 
        raise NotImplementedError("Delete user is not implemented yet.")

    def validate_reset_password_token(self, user: User, token: str) -> UserPasswordReset | None:
        """
        Validate a password reset token for a user.
        Note: If the token is expired, it will be deleted from the database.
        :param user: The User object to validate the token for.
        :param token: The token to validate.
        :return: The UserPasswordReset object if the token is valid, None otherwise.
        """
        token = self.session.exec(
            select(UserPasswordReset)
            .where(UserPasswordReset.token == token)
            .where(UserPasswordReset.user_id == user.id)
        ).first()

        if token and token.expires_at < datetime.now():
            self.session.delete(token)
            self.session.commit()

        return token

    def delete_reset_password_token(self, user: User, token: str) -> bool:
        """
        Delete a password reset token for a user.
        :param user: The User object to delete the token for.
        :param token: The token to delete.
        :return: True if the token was deleted, raise an exception otherwise.
        """
        token = self.validate_reset_password_token(user, token)
        if token:
            self.session.delete(token)
            self.session.commit()
            return True
        return False
    
    def validate_password(self, password: str) -> bool:
        """
        Validate a password according to the following rules:
        - At least 12 characters long
        - At least one digit
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one special character
        :param password: The password to validate.
        :return: True if the password is valid, False otherwise.
        """
        if len(password) <= 12:
            return False
        if not any(char.isdigit() for char in password):
            return False
        if not any(char.isupper() for char in password):
            return False
        if not any(char.islower() for char in password):
            return False
        if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
            return False
    
    def set_user_password(self, user: User, password: str) -> bool:
        """
        Set the password for a user.
        """
        user.password = hash_password(password)
        self.session.add(user)
        self.session.commit()
        
    def reset_password(self, username: str, token: str, password) -> bool:
        """
        Reset the password for a user.
        """
        user = self.get_user_by_name(username)
        if not user:
            return False
        
        if not self.validate_reset_password_token(user, token):
            return False

        if not self.validate_reset_password_token(password):
            return False

        self.set_user_password(user, password)
        self.delete_reset_password_token(user, token)
        return True
