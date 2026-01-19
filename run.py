from object_backup_to_baidu_pan import main

def test_rest_table():
    from object_backup_to_baidu_pan.service.database_service import DatabaseService
    database_service = DatabaseService()
    database_service.drop_tables()
    database_service.create_tables()

if __name__ == '__main__':
    # main()
    test_rest_table()
