from datetime import datetime
from fob_api.models import database as db
from fob_api import auth 
from sqlmodel import select

class TokenManager:

    """
    TokenManager is responsible for managing user tokens for authentication.
    """
    
    session = None

    def __init__(self, session):
        self.session = session
    
    def create_token(self, user: db.User):
        """
        Create a new token for the user.
        """
        token_data = auth.make_token_data(user.username)
        token_db: db.Token = db.Token(
            expires_at=token_data["exp"],
            created_at=token_data["iat"],
            token_id=token_data["jti"],
            user_id=user.id,
        )
        self.session.add(token_db)
        self.session.commit()
        token = auth.encode_token(token_data)
        return token

    def get_token(self, token_id: str) -> db.Token | None:
        """
        Get a token from the database.
        """
        return self.session.exec(select(db.Token).where(db.Token.token_id == token_id)).first()
    
    def list_token(self, user_id: int) -> list[db.Token]:
        """
        List all tokens for a user.
        """
        return self.session.exec(select(db.Token).where(db.Token.user_id == user_id)).all()

    def delete_token(self, token_id: str):
        """
        Delete a token from the database.
        """
        token = self.session.exec(select(db.Token).where(db.Token.token_id == token_id)).first()
        if token:
            self.session.delete(token)
            self.session.commit()

    def validate_token(self, token_id: str) -> bool:
        """
        Validate a token
        """
        token = self.get_token(token_id)
        if not token:
            return False
        if token.expires_at < datetime.now():
            return False
        return True