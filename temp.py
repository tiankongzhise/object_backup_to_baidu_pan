

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

if __name__ == '__main__':
    # test_is_expired_in_day()
    # test_init_db()
    test_refresh_token()
    # test_enumerate()
