# This file intentionally contains insecure SQL construction for Semgrep testing.

username = "admin"

query = "SELECT * FROM users WHERE username = '" + username

sql_query = f"SELECT * FROM users WHERE username = '{username}'"

statement = "SELECT * FROM users WHERE username = '{}'".format(username)
