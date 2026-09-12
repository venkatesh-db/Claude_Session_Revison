from github import Auth, Github


def create_client_from_token(token: str) -> Github:
    if not token:
        raise ValueError("A GitHub token is required.")
    return Github(auth=Auth.Token(token))
