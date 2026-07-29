import sqlite3
import time
import csv
import sys
import getpass
from typing import Optional
#Importing necessary features, including sqlite3, time, csv, sys (for system exits) and getpass (To hide password input)

class Inventory:
    # Defining the __init__ function, sets the db_file name table_name based on information passed
    def __init__(self, db_file="inventory.db", table_name="products"):
        self.db_file = db_file
        self.table_name = table_name
        self.create_table_if_missing()

    def create_table_if_missing(self):
        # Changed to an f-string to parse self.table_name correctly
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS {self.table_name}
                   (prodname TEXT NOT NULL,
                    timemade TEXT NOT NULL,
                   prodcat TEXT NOT NULL,
                   prodid TEXT PRIMARY KEY NOT NULL,
                   prodstock INTEGER NOT NULL,
                   prodopid TEXT);''')
            connection.commit()
        # Table to track authentication lockouts / logins
            cursor.execute(f'''CREATE TABLE IF NOT EXISTS auth_lockout
                            (id INTEGER PRIMARY KEY,
                            failed_attempts INTEGER NOT NULL,
                            lockout_until REAL NOT NULL);''')

            cursor.execute("INSERT OR IGNORE INTO auth_lockout (id, failed_attempts, lockout_until) VALUES (1, 0, 0)")

    # Method used to get the amount of failed attempts from the authentication table
    def get_auth_state(self):
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT failed_attempts, lockout_until FROM auth_lockout WHERE id = 1")
            return cursor.fetchone()

    # Method used to set the number of failed attempts and lockout time
    def update_auth_state(self, failed_attempts, lockout_until):
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE auth_lockout SET failed_attempts = ?, lockout_until = ? WHERE id = 1",
                (failed_attempts, lockout_until)
            )
            connection.commit()

    # Used to add items to the database
    def add_item(self, name, timemade, category, prod_id, stock, optional_id=None):
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()

            if optional_id in (None, "", "None"):
                cursor.execute(
                    f"INSERT INTO {self.table_name} (prodName, timemade, prodcat, prodID, prodStock) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (name, timemade, category, prod_id, stock),
                )
            else:
                cursor.execute(
                    f"INSERT INTO {self.table_name} (prodName, timemade, prodcat, prodID, prodStock, prodopid) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (name, timemade, category, prod_id, stock, optional_id),
                )
            connection.commit()


    def get_all_rows(self):
        # Returns every row as a list of tuples
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            return cursor.fetchall()

    def search_by_id(self, prod_id):
        # Returns a single row by ID or none if not found
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT * FROM {self.table_name} WHERE prodID = ?", (prod_id,)
            )
            return cursor.fetchone()

    # Updates the time for auditing purposes by product ID anytime it's accessed 
    def update_time(self, prod_id, new_time):
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET timemade = ? WHERE prodID = ?",
                (new_time, prod_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def update_stock(self, prod_id, new_stock):
        # Returns true if a row is found and false if not; meant to update stock
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET prodStock = ? WHERE prodID = ?",
                (new_stock, prod_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def delete_product(self, prod_id):
        # Returns true if a row is found and false if not; meant to delete a product
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"DELETE FROM {self.table_name} WHERE prodID = ?", (prod_id,)
            )
            connection.commit()
            return cursor.rowcount > 0

    def update_name(self, prod_id, new_name):
        # Returns true if a row is found and false if not; meant to update a products name
        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET prodname = ? WHERE prodID = ?", (new_name, prod_id)
            )
            connection.commit()
            return cursor.rowcount > 0

    def sort_by(self, category):
        # Returns every row ordered by the given column
        columns = {"prodname", "timemade", "prodcat", "prodid", "prodstock"}
        if category not in columns:
            raise ValueError(f"Invalid sort column: {category}")

        with sqlite3.connect(self.db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} ORDER BY {category}")
            return cursor.fetchall()


class InventoryCLI:
    # Dictionary to easily implement new categories and such
    CATEGORIES = {
        "1": "Clothing",
        "2": "Footwear",
        "3": "Accessories",
        "4": "Computer/Laptops",
        "5": "Phones",
        "6": "Audio & Video",
        "7": "Wearables",
        "8": "Furniture",
        "9": "Home Decor",
        "10": "Health/Beauty",
        "11": "Sports/Fitness",
        "12": "Toys",
        "13": "Food",
        "14": "Office Supplies",
    }

    # Menu used for the sort-by feature
    SORT_OPTIONS = {
        "1": ("Name", "prodname"),
        "2" :("Time", "timemade"),
        "3": ("Category", "prodcat"),
        "4": ("Product ID", "prodid"),
        "5": ("Stock", "prodstock"),
    }

    # Dictionary of allowed users 
    ALLOWED_USERS = {
        "makoto" : "burnmydread",
        "yu" : "pursuingmytrueself",
        "ren" : "wakeupgetup",
    }

    # __init__ to initialize the self and inventory classes
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.current_user: Optional[str] = None

    # Login prompt to check if input information is correct + lockout system for auditing
    def prompt_login(self):

        max_attempts = 3
        lockout_duration = 60
        

        while True:
            failed_attempts, lockout_until = self.inventory.get_auth_state()
            current_time = time.time()

            if current_time < lockout_until:
                remaining = int(lockout_until - current_time)
                print(f"INVALID LOGIN LOCKOUT\nPlease wait {remaining} seconds before trying to login again.")
                sys.exit()
            
            print("Name:")
            name = input(">>").strip()
            password = getpass.getpass("Enter your password:")

            if (name in self.ALLOWED_USERS and self.ALLOWED_USERS[name] == password):
                print(f"\nLogin successful! Welcome, {name}.\n")
                return name

            failed_attempts += 1  
            print("Invalid username or password, please try again.")

            if failed_attempts >= max_attempts:
                print(f"Locking system out for failed attempts.")
                self.inventory.update_auth_state(0, current_time + lockout_duration)
                sys.exit()
            else:
                self.inventory.update_auth_state(failed_attempts, 0)


    # Function used to prompt name
    def prompt_name(self):
        while True:
            print("New Product Entry Name")
            name = input(">>").strip()
            if name == "":
                print("Invalid Entry")
            else:
                return name

    # Function used to grab the approx time an item was catalogued or changed
    def time_setter(self) -> str:
        clock = time.localtime()
        format_min = time.strftime("%M", clock)
        user = self.current_user if self.current_user else "System"
        clock_formatted = f"{clock.tm_mon}-{clock.tm_mday}-{clock.tm_year} at {clock.tm_hour}:{format_min} by {user}"
        return clock_formatted
    
    # Function used to prompt category
    def prompt_category(self):
        while True:
            print("New Product Category")
            print("""Clothing[1]\nFootwear[2]\nAccessories[3]\nComputers/Laptops[4]
Phones[5]\nAudio & Video[6]\nWearables[7]\nFurniture[8]
Home Decor[9]\nHealth/Beauty[10]\nSports/Fitness[11]\nToys[12]
Food[13]\nOffice Supplies[14]""")
            choice = input(">>").strip()
            if choice in self.CATEGORIES:
                return self.CATEGORIES[choice]
            print("Invalid Category")

    # Function used to prompt product ID
    def prompt_prod_id(self):
        while True:
            print("New Product Entry ID")
            prod_id = input(">>").strip()
            if prod_id == "":
                print("Invalid ID")
            else:
                return prod_id

    # Function used to prompt stock
    def prompt_stock(self):
        while True:
            print("New Product Current Amount In Stock")
            stock = input(">>").strip()
            if not stock.isdigit():
                print("Invalid Stock Amount")
            else:
                return int(stock)

    # Function used to prompt the optional id
    def prompt_optional_id(self):
        print("Optional Extra ID: Type N or n to skip")
        optional_id = input(">>").strip()
        if optional_id in ("N", "n", ""):
            return None
        return optional_id

    # Method that combines all the prompts to add an item
    def add_item(self):
        name = self.prompt_name()
        timemade = self.time_setter()
        category = self.prompt_category()
        prod_id = self.prompt_prod_id()
        stock = self.prompt_stock()
        optional_id = self.prompt_optional_id()

        try:
            self.inventory.add_item(name, timemade, category, prod_id, stock, optional_id)
            if optional_id is None:
                print("Product added successfully.")
            else:
                print("Product added successfully with optional ID.")
        except sqlite3.IntegrityError:
            print("Error: A product with this ID already exists.")

    # Helper that prints a single page of rows in the shared table format
    def print_rows_page(self, rows, page, total_pages):
        page_size = 10
        start_index = page * page_size
        end_index = start_index + page_size
        current_rows = rows[start_index:end_index]

        print(f"\nPage {page + 1}/{total_pages}")
        print("Product Name | Last Time Accessed | Product Category | Product ID | Product Stock | Optional ID")
        for row in current_rows:
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {str(row[4])} | {row[5] if row[5] else 'Null'}")

    # Method that prints all rows of items, with an optional sort applied first


    # Method that exports the inventory database as a CSV file, sorted by choice of user

    def export_file(self):
            sort_choice = self.prompt_sort_choice()
    
            if sort_choice is None:
                rows = self.inventory.get_all_rows()
            else:
                rows = self.inventory.sort_by(sort_choice)
    
            if not rows:
                print("No rows to export.")
                return
    
            filename = input("Please enter the name for the CSV file:")
            if not filename:
                filename = "inventory_output.csv"
            elif not filename.endswith(".csv"):
                filename += ".csv"
    
            try:
                with open(filename, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
    
                    writer.writerow([
                    "Product Name",
                    "Last Time Accessed",
                    "Product Category",
                    "Product ID",
                    "Stock Quantity",
                    "Optional ID"
                    ])
    
                    for row in rows:
                        writer.writerow([
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5] if row[5] else ""
                        ])
    
                    print(f"Successfuly exported items to file!")
    
            except Exception as e:
                print(f"An error has occurred while exporting the file: {e}")

        
    def print_all_rows(self):
        sort_choice = self.prompt_sort_choice()
        if sort_choice is None:
            rows = self.inventory.get_all_rows()
        else:
            rows = self.inventory.sort_by(sort_choice)

        if not rows:
            print("No products found in the database.")
            return

        page_size = 10
        total_pages = (len(rows) + page_size - 1) // page_size
        page = 0

        while True:
            self.print_rows_page(rows, page, total_pages)

            if total_pages == 1:
                break

            print("\nOptions: [P] Next Page, [O] Past Page, [E]xit")
            choice = input("Enter your choice: ").strip().lower()

            if choice == 'p' and page < total_pages - 1:
                page += 1
            elif choice == 'o' and page > 0:
                page -= 1
            elif choice == 'e':
                break
            else:
                print("There are no more pages in that direction.")


    # Method run after printing all items in order to sort by given category

    def prompt_sort_choice(self):
        print("\nSort by:")
        print("Name[1]\nTime[2]\nCategory[3]\nProduct ID[4]\nStock[5]\nNo Sort[N]")
        choice = input(">>").strip().lower()
        if choice in ("n", ""):
            return None
        if choice in self.SORT_OPTIONS:
            return self.SORT_OPTIONS[choice][1]
        print("Invalid choice, showing unsorted results.")
        return None

    # Method for searching a product by ID

    def search_by_id(self):
        prod_id = input("Enter the product ID to search for: ").strip()
        row = self.inventory.search_by_id(prod_id)
        if row:
            print(
                f"Product with ID {prod_id}: {row[0]}\n"
                f"Time Updated: {row[1]}\n"
                f"Product Category: {row[2]}\n"
                f"Product ID: {row[3]}\n"
                f"Product Stock: {row[4]}\n"
                f"Optional: {row[5] if row[5] else 'Null'}"
            )
        else:
            print(f"No product found with ID {prod_id}")

    # Method for updating the stock of an item

    def update_stock(self):
        prod_id = input("Enter the product ID to update: ").strip()
        row = self.inventory.search_by_id(prod_id)
        if not row:
            print(f"No product found with ID {prod_id}")
            return

        current_stock = row[4]
        print(f"Current stock for {prod_id}: {current_stock}")
        print("[S] Set exact stock value, [+] Increase stock, [-] Decrease stock")
        mode = input("Enter your choice: ").strip().lower()

        if mode == "s":
            new_stock = input("Enter the new stock quantity: ").strip()
            if not new_stock.isdigit():
                print("Invalid stock number.")
                return
            final_stock = int(new_stock)
        elif mode == "+":
            amount = input("Enter the amount to increase stock by: ").strip()
            if not amount.isdigit():
                print("Invalid stock number.")
                return
            final_stock = current_stock + int(amount)
        elif mode == "-":
            amount = input("Enter the amount to decrease stock by: ").strip()
            if not amount.isdigit():
                print("Invalid stock number.")
                return
            decrement = int(amount)
            if decrement > current_stock:
                print("Cannot reduce stock below 0")
                return
            final_stock = current_stock - decrement
        else:
            print("Invalid choice.")
            return

        updated = self.inventory.update_stock(prod_id, final_stock)

        new_time = self.time_setter()
        updated_time = self.inventory.update_time(prod_id, new_time)

        if updated and updated_time:
            print(f"Product with ID {prod_id} updated to new stock: {final_stock}")
            
        else:
            print(f"No product found with ID {prod_id}")

    # Method for deleting a product by ID

    def delete_product(self):
        prod_id = input("Enter the product ID to delete: ").strip()
        deleted = self.inventory.delete_product(prod_id)
        if deleted:
            print("Product has been deleted")
        else:
            print("Product not found")

    # Method for updating the name of a product by ID
    
    def update_name(self):
        prod_id = input("Enter the product ID to change the name: ").strip()
        new_name = input("Enter the new name for the product: ").strip()
        changed_name = self.inventory.update_name(prod_id, new_name)

        new_time = self.time_setter()
        updated_time = self.inventory.update_time(prod_id, new_time)

        if changed_name and updated_time:
            print(f"Product has had name changed to: {new_name}")
        else:
            print("Product not found")

    # Method to run the entire main menu
    def run(self):

        self.current_user = self.prompt_login()

        while True:
            print("\n Inventory Management System:")
            print("1. Print all items")
            print("2. Add a new item")
            print("3. Search by ID")
            print("4. Update stock")
            print("5. Update a name")
            print("6. Delete a product")
            print("7: Export a CSV File")
            print("8: Close the program")

            choice = input("Enter your choice (1-8): ").strip()

            if choice == "1":
                self.print_all_rows()
            elif choice == "2":
                self.add_item()
            elif choice == "3":
                self.search_by_id()
            elif choice == "4":
                self.update_stock()
            elif choice == "5":
                self.update_name()
            elif choice == "6":
                self.delete_product()
            elif choice == "7":
                self.export_file()
            elif choice == "8":
                print("Exiting the program.")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 8.")


if __name__ == "__main__":
    inventory = Inventory()
    cli = InventoryCLI(inventory)
    cli.run()
