import requests
import aiohttp
class InfluxDB:
    def __init__(self, base_url, api_token, organization, bucket, instance_name):
        self.instance_name = instance_name
        self.url = f"{base_url}/api/v2/write?org={organization}&bucket={bucket}&precision=s"
        self.headers = {"Authorization": f"Token {api_token}"}

    def write(self, fields: dict, tags: dict, timestamp: int):
        try:
            data = self._format_data(fields, tags, timestamp)
            response = requests.post(self.url, headers=self.headers, data=data, timeout=2)
            if response.status_code != 204:
                raise Exception(f"Error writing to InfluxDB: {response.text}")
            return True
        except Exception as e:
            return False

    async def async_write(self, fields: dict, tags: dict, timestamp: int):
        try:
            data = self._format_data(fields, tags, timestamp)
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, data=data, headers=self.headers) as response:
                    if response.status != 204:
                        error_text = await response.read()
                        raise Exception(f"Error writing to InfluxDB: {error_text}")
                    return True
        except Exception as e:
            return False

    @staticmethod
    def _format(dict_data: dict) -> str:
        return ",".join(f'{k}={v}' for k, v in dict_data.items())

    def _format_data(self, fields: dict, tags: dict, timestamp: int) -> str:
        tag_set = InfluxDB._format(tags)
        field_set = InfluxDB._format(fields)
        data = f"{self.instance_name},{tag_set} {field_set} {timestamp}"
        return data