import requests
import aiohttp
import asyncio
from singleton import singleton
from time_keeper import TimeKeeper

time_keeper = TimeKeeper()

@singleton
class InfluxDB:
    instance_name: str
    url: str
    headers: dict
    configured: bool

    def __init__(self):
        self.configured = False

    def config(self, base_url, api_token, organization, bucket, instance_name):
        self.instance_name = instance_name
        self.url = f"{base_url}/api/v2/write?org={organization}&bucket={bucket}&precision=s"
        self.headers = {"Authorization": f"Token {api_token}"}
        self.configured = True


    def write(self, fields: dict, tags: dict, timestamp: int=None):
        if timestamp is None:
            timestamp = time_keeper.get_epoch()
        if not self.configured:
            raise Exception("InfluxDB not configured. Call config() method first.")
        try:
            data = self._format_data(fields, tags, timestamp)
            response = requests.post(self.url, headers=self.headers, data=data, timeout=2)
            if response.status_code != 204:
                raise Exception(f"Error writing to InfluxDB: {response.text}")
            return True
        except Exception as e:
            return False

    async def async_write(self, fields: dict, tags: dict, timestamp: int=None):
        if timestamp is None:
            timestamp = time_keeper.get_epoch()
        if not self.configured:
            raise Exception("InfluxDB not configured. Call config() method first.")
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

    # a good name fot the method that will write data to influxdb triggering an async write but not waiting for the result. It should nor be "async_write" or "write_async".
    def fire_write(self, fields: dict, tags: dict, timestamp: int=None):
        asyncio.create_task(
            self.async_write(fields, tags, timestamp)
        )

    @staticmethod
    def _format(dict_data: dict) -> str:
        fields = []
        for k, v in dict_data.items():
            if isinstance(v, str):
                # Wrap strings in double quotes
                fields.append(f'{k}="{v}"')
            elif isinstance(v, bool):
                # Format booleans in lowercase
                fields.append(f'{k}={"true" if v else "false"}')
            else:
                fields.append(f'{k}={v}')
        return ",".join(fields)

    def _format_data(self, fields: dict, tags: dict, timestamp: int) -> str:
        tag_set = self._format(tags)
        field_set = self._format(fields)
        data = f"{self.instance_name},{tag_set} {field_set} {timestamp}"
        return data