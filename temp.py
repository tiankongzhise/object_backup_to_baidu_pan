

def test_is_expired_in_day():
    from object_backup_to_baidu_pan.service.upload_service.database.client import OauthDbClient
    client = OauthDbClient()
    token_item = client.get_token()
    print(token_item.is_expired_in_day)

def test_init_db():
    from object_backup_to_baidu_pan.service.upload_service.oauth import init_oauth_db
    result = init_oauth_db()
    print(result)

def test_refresh_token():
    from object_backup_to_baidu_pan.service.upload_service.oauth import oauthtoken_refreshtoken
    result = oauthtoken_refreshtoken()
    print(result)

def test_enumerate():
    for i, item in enumerate([1, 2, 3]):
        print(i, item)

def compare_hash(file1, file2):
    from object_backup_to_baidu_pan.service.hash_service import CalculateHashService
    from pathlib import Path
    path1 = Path(r'D:\测试用例\normal_folder')
    path2 = Path()
    hash_service = CalculateHashService()
    hash_1 = hash_service.calculate_folder_hash(path1)
    hash_2 = hash_service.calculate_folder_hash(path2)
    for key,value in hash_1.items():
        if key in hash_2 and hash_2[key] == value:
            print(f'hash:{key} is equal')
        else:
            print(f'path1:{path1} hash:{key} is {value},path2:{path2} hash:{key} is {hash_2[key]}')

if __name__ == '__main__':
    # test_is_expired_in_day()
    # test_init_db()
    test_refresh_token()
    # test_enumerate()
