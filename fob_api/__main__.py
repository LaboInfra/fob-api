"""
This script create or update user password and give admin right
this is not a part of the app, this is a helper script to initialize the app
"""
from sys import argv

from sqlmodel import Session, select

from . import engine
from .database import create_db_and_tables
from .models import User
from .auth import hash_password


def main() -> None:
    """
    Main function to create or update user password and give admin right
    :param argv: take username as argument
    :return: None
    """
    # check if username is provided
    print("This script create or update user password and give admin right")
    if len(argv) <= 3:
        print("Please provide email to create and password tow times")
        return

    email = argv[1]
    username = email.split("@")[0]
    password = argv[2]
    password_confirm = argv[3]

    if password != password_confirm:
        print("Password is not eq")
        return

    # create or update user
    with Session(engine) as session:
        # check if user already exists if not create new user
        user: User = session.exec(select(User).filter(User.username == username)).first()
        if not user:
            print("User not found creating new user")
            user = User(username=username)

        # set password and admin rights
        user.password = hash_password(password)
        user.email = email
        user.is_admin = True
        session.add(user)
        session.commit()

        # print user information
        print("User created or updated")
        print("Username: ", user.username)
        print("Admin rights given")


# run main function
if __name__ == "__main__":
    create_db_and_tables(engine)
    main()