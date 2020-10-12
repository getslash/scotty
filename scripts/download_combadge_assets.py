import datetime
import io
import os
import zipfile

import requests


artifacts_response = requests.get('https://api.github.com/repos/getslash/scotty/actions/artifacts')
artifacts_response.raise_for_status()
artifacts_json = artifacts_response.json()
assert 'artifacts' in artifacts_json, f"Artifacts: {artifacts_json}"
artifacts = artifacts_json['artifacts']
auth = (os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
artifacts = sorted(artifacts, key=lambda x: datetime.datetime.strptime(x['updated_at'], '%Y-%m-%dT%H:%M:%SZ'), reverse=True)[:3]

combadge_assets = os.path.join(os.path.dirname(__file__), os.pardir, 'combadge_assets', 'v2')
os.makedirs(combadge_assets, exist_ok=True)

for artifact in artifacts:
    artifact_content_response = requests.get(artifact['archive_download_url'], auth=auth)
    artifact_content_response.raise_for_status()
    content = artifact_content_response.content
    file = io.BytesIO(content)
    file.seek(0)
    with zipfile.ZipFile(file) as z:
        z.extractall(path=os.path.join(combadge_assets, artifact['name'].replace('_asset', '')))

