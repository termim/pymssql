import pymssql

con = pymssql.connect(
        server='localhost',
        user='sa',
        password='sqlServerPassw0rd',
        database='tempdb',
        port=1433,
    )
