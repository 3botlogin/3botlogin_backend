# 3botlogin_backend
The (temporary) backend for 3Bot login.

## Data to save
### User
A user is someone that authenticates using 3botlogin.
| Key | Type | Example | Description |
| --- | --- | --- | --- |
| doubleName | String | ivan.coene | The name of the user (case insensitive) | 
| publicKey | string | G1gcbyeTnR2i...H8_3yV3cuF | The public key of the user to verify access |


### Login attempt
When a user tries to log in, an entry is added
| Key | Type | Example | Description |
| --- | --- | --- | --- |
| doubleName | String | ivan.coene | The name of the user (case insensitive) | 
| stateHash | String | 1gcbyeTnR2iZSfx6r2qIuvhH8 | The "identifier" of a login-attempt |
| timeStamp | Datetime | 2002-12-25 00:00:00-06:39 | The time when this satehash came in |
| scanned | Boolean | false | Flag to keep the QR-scanned state |
| singedStateHash | String | 1gcbyeTnR2iZSfx6r2qIuvhH8 | The signed version of the state hash|

## Run in dev mode
To run the backend in devmode simply execute following command
```
python3 .
```