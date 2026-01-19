import os
from pprint import pprint
from dotenv import load_dotenv
from . import openapi_client
from .openapi_client.api import auth_api
from .database.client import OauthDbClient
from .database.models import BaiduPanOauth
   

def update_local_env_token(token_item:BaiduPanOauth,env_path = '.env'):
    print("env file baidu pan access token is not latest, updating env file")
    env_key_to_token_item = {
        'BAIDU_PAN_ACCESS_TOKEN': token_item.access_token,
        'BAIDU_PAN_REFRESH_TOKEN': token_item.refresh_token,
        'BAIDU_PAN_APP_KEY': token_item.client_id,
        'BAIDU_PAN_SECRET_KEY': token_item.client_secret
    }
    with open(env_path, 'r') as f:
        lines = f.readlines()
    token_about_line = {'BAIDU_PAN_ACCESS_TOKEN': None, 'BAIDU_PAN_REFRESH_TOKEN': None, 'BAIDU_PAN_APP_KEY': None, 'BAIDU_PAN_SECRET_KEY': None}
    for index, line in enumerate(lines):
        if line.startswith('BAIDU_PAN_ACCESS_TOKEN'):
            token_about_line['BAIDU_PAN_ACCESS_TOKEN'] = index
        elif line.startswith('BAIDU_PAN_REFRESH_TOKEN'):
            token_about_line['BAIDU_PAN_REFRESH_TOKEN'] = index
        elif line.startswith('BAIDU_PAN_APP_KEY'):
            token_about_line['BAIDU_PAN_APP_KEY'] = index
        elif line.startswith('BAIDU_PAN_SECRET_KEY'):
            token_about_line['BAIDU_PAN_SECRET_KEY'] = index
    for key, value in token_about_line.items():
        if value is not None:
            lines[value] = f"{key}={env_key_to_token_item[key]}\n"  # Updated line
        else:
            lines.append(f"{key}={env_key_to_token_item[key]}\n")  # Updated line
    print(lines)
    with open(env_path, 'w') as f:
        f.writelines(lines)

def oauthtoken_refreshtoken(env_path = '.env'):
    """
    refresh access token
    """
    # Enter a context with an instance of the API client
    mysql_client = OauthDbClient()
    token_item = mysql_client.get_token()
    if not token_item:
        init_oauth_db()
        token_item = mysql_client.get_token()


    if not token_item.is_expired_in_day:
        load_dotenv(env_path)
        local_access_token = os.getenv('BAIDU_PAN_ACCESS_TOKEN','')
        if local_access_token == token_item.access_token:
            print("baidu pan access token not expired, no need to refresh")
            return
        else:
            update_local_env_token(token_item,env_path)
    print("baidu pan access token expired, refreshing")
    with openapi_client.ApiClient() as api_client:
        # Create an instance of the API class
        api_instance = auth_api.AuthApi(api_client)
        refresh_token = token_item.refresh_token # str | 
        client_id = token_item.client_id # str | 
        client_secret = token_item.client_secret # str | 

        # example passing only required values which don't have defaults set
        try:
            api_response = api_instance.oauth_token_refresh_token(refresh_token, client_id, client_secret)
            try:
                mysql_client.add_token({'access_token': api_response['access_token'], 'refresh_token': api_response['refresh_token'],'expires_in': api_response['expires_in'],'client_id': client_id,'client_secret': client_secret})
            except Exception as e:
                 raise Exception(f"Failed to update token in database,errmsg:{e}")
            latest_token_item = mysql_client.get_token()
            if latest_token_item:
                update_local_env_token(latest_token_item,env_path)
            else:
                raise Exception("Failed to get latest token after refreshing")
        except openapi_client.ApiException as e:
            print("Exception when calling AuthApi->oauth_token_refresh_token: %s\n" % e)



def init_oauth_db(client_id:str|None = None, client_secret:str|None = None, access_token:str|None = None,refresh_token:str|None = None, expires_in:int|None = None,env_path = '.env'):
    """
    Initialize the oauth database with the provided access token, refresh token, and expires in values.
    If no values are provided, the function will use the environment variables.
    """
    load_dotenv(env_path)   
    init_client_id = client_id or os.getenv('BAIDU_PAN_APP_KEY')
    if not init_client_id:
        raise ValueError("Client ID is required")
    init_client_secret = client_secret or os.getenv('BAIDU_PAN_SECRET_KEY')
    if not init_client_secret:
        raise ValueError("Client secret is required")
    init_access_token = access_token or os.getenv('BAIDU_PAN_ACCESS_TOKEN')
    if not init_access_token:
        raise ValueError("Access token is required")
    init_refresh_token = refresh_token or os.getenv('BAIDU_PAN_REFRESH_TOKEN')
    if not init_refresh_token:
        raise ValueError("Refresh token is required")
    init_expires_in = expires_in or 0
    client = OauthDbClient()
    client.reset_table()
    client.add_token({
        'client_id': init_client_id,
        'client_secret': init_client_secret,
        'access_token': init_access_token,
        'refresh_token': init_refresh_token,
        'expires_in': init_expires_in

    })
    return client.get_token()
