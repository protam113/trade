import keyring

SERVICE_NAME = "TradeTracker"  # app name

# save password
keyring.set_password(SERVICE_NAME, "main_account", "3kP!YmVv")

# get password
pw = keyring.get_password(SERVICE_NAME, "main_account")
print(pw)  # "3kP!YmVv"

# delete password khi logout
keyring.delete_password(SERVICE_NAME, "main_account")
