from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title='Mock Third Party Auth')


class LoginPayload(BaseModel):
    account: str
    password: str


@app.post('/mock-auth')
def mock_auth(payload: LoginPayload) -> dict:
    if payload.password == '123456':
        return {
            'success': True,
            'code': 200,
            'data': {
                'name': f'用户{payload.account}',
                'accountId': payload.account,
                'avatarUrl': '',
                'idNumber': '',
            },
        }
    return {'success': False, 'msg': '请检查账号密码', 'code': 401}
