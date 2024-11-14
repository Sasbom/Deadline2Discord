import os


print("Reading env")

user = os.environ.get("PG_USER")
pwd = os.environ.get("PG_PWD")
db = os.environ.get("PG_DB")

write_str = (f"CREATE USER {user} WITH PASSWORD '{pwd}';\n"
             f"CREATE IF NOT EXISTS DATABASE {db};\n"
             f"GRANT ALL PRIVILEGES ON DATABASE {db} TO {user};\n")

print(write_str)
with open("/sql/init.sql", "w") as file:
    file.write(write_str)


exit(0)