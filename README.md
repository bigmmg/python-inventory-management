A lightweight, command line interface based application built in Python using SQLite3 as the database. It allows users of any small company to manage inventories, log and make changes, track updates, and export to CSV files. Created for an internship at Goodwill, but open source for anyone who needs to use it.

Features include:
- Authentication System: Using a secure login system with hidden password entry and a lockout mechanism
- Database Management: SQLite directly interacts with the database, allowing anyone to make changes by using just the program
- Audit Logging: Uses the time module to stamp the exact time a user updates a product or creates a product
- Sorting: Sort through items and scroll through large catalogs 10 items per page (easily customizable)
- Data Export: Easily export database to CSV file

Python 3.x is a requirement, along with standard Python libraries including.
- sqlite3
- time
- csv
- sys
- getpass

To run, clone/download the repository and run the main script.
Default login credentials are:
- makoto: burnmydread
- yu: pursuingmytrueself
- ren: wakeupgetup

The database is structured as follows:
- products (table): stores values including prodname, timemade, prodcat, prodid (ONLY ONE FOR EACH ITEM), prodstock, and prodopid
- auth_lockout (table): keeps track of failed login attempts and lockout times
