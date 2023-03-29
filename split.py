import json
import requests
import sys

# URL to the Stash instance
STASH_URL = 'http://localhost:9999/graphql'

# API Key from Stash (URL/settings?tab=security)
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJhbmdlbG8iLCJpYXQiOjE2NzM2NzkxMTUsInN1YiI6IkFQSUtleSJ9.bTkxq90xYnstHO9LpW2hkxRQBC-N3jjy3eq7OHn4-lY"

tag_ids = [None]

TAGS_EXCLUDE = ["Split Scenes: Ignore"]


class SplitWith:
    """
    Main plugin class
    """
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
    }

    def __init__(self, STASH_URL, API_KEY):
        self.STASH_URL = STASH_URL
        self.headers["ApiKey"] = API_KEY

    def __prefix(self, levelchar):
        startlevelchar = b'\x01'
        endlevelchar = b'\x02'

        ret = startlevelchar + levelchar + endlevelchar
        return ret.decode()

    def __log(self, levelchar, error_code):
        if levelchar == "":
            return
        if error_code == "":
            return

        print(self.__prefix(levelchar) + error_code +
              "\n", file=sys.stderr, flush=True)

    def trace(self, error_code):
        self.__log(b't', error_code)

    def debug(self, error_code):
        self.__log(b'd', error_code)

    def info(self, error_code):
        self.__log(b'i', error_code)

    def warning(self, error_code):
        self.__log(b'w', error_code)

    def error(self, error_code):
        self.__log(b'e', error_code)

    def progress(self, p):
        progress = min(max(0, p), 1)
        self.__log(b'p', str(progress))

    def __callGraphQL(self, query, variables=None):
        json = {}
        json['query'] = query
        if variables != None:
            json['variables'] = variables

        # handle cookies
        response = requests.post(
            self.STASH_URL, json=json, headers=self.headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("error", None):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data", None):
                return result.get("data")
        elif response.status_code == 401:
            self.error(
                "[ERROR][GraphQL] HTTP Error 401, Unauthorised. You can add a API Key in at top of the script")
            return None
        else:
            raise Exception(
                "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(response.status_code, response.content,
                                                                                query, variables))

    def findTagIdWithName(self, tag_name):
        query = """
            query {
                allTags {
                    id
                    name
                }
            }
        """
        result = self.__callGraphQL(query)
        for tag in result["allTags"]:
            if tag["name"] == tag_name:
                return tag["id"]
        return None

    def createTagWithName(self, name):
        query = """
mutation tagCreate($input:TagCreateInput!) {
  tagCreate(input: $input){
    id       
  }
}
"""
        variables = {'input': {
            'name': name
        }}

        result = self.__callGraphQL(query, variables)
        return result["tagCreate"]["id"]

    def removeTagWithID(self, id):
        query = """
                mutation tagDestroy($input: TagDestroyInput!) {
                tagDestroy(input: $input)
                }
                """
        variables = {'input': {
            'id': id
        }}
        self.__callGraphQL(query, variables)

    def setup_tags(self):
        for tag_name in TAGS_EXCLUDE:
            tag_id = self.findTagIdWithName(tag_name)
            self.error("tag_name: "+tag_name)

            if tag_id is None:
                tag_id = self.createTagWithName(tag_name)
                self.debug("Adding tag: "+tag_name)
            else:
                self.error("Tag already exists: "+tag_name)
        # upscaled = self.findTagIdWithName(self, TAGS_EXCLUDE)

    def remove_tags(self):
        for tag_name in TAGS_EXCLUDE:
            tag_id = self.findTagIdWithName(tag_name)
            if tag_id is None:
                self.error("Error: "+tag_name + "doesn't exist")
            else:
                self.debug("Removing tag: , "+tag_name)
                self.removeTagWithID(tag_id)

    def findTags(self, tag):
        # Finds scenes with studio
        query = """
                query findTag($findTag: TagFilterType!){
                findTags(tag_filter: $findTag){
                    tags {
                    name
                    id
                    }
                }
                }
        """

        variables = {
            "findTag": {
                "name": {
                    "value": tag,
                    "modifier": "MATCHES_REGEX"
                }
            }
        }
        result = self.__callGraphQL(query, variables)
        tags = []
        for foundTag in result["findTags"]["tags"]:
            id = foundTag["id"]
            tags.append((id))
        return tags

    def findScenes(self, tagIds):
        # Finds scenes with studio
        query = """
        query fundMultipleScenes ($findMultipleScenes: SceneFilterType!) {
        findScenes(scene_filter: $findMultipleScenes, filter: {per_page: -1}) {
            scenes {
            files {
                id
                path
            }
            tags {
                id
            }
            }
        }
        }
        """
        variables = {
            "findMultipleScenes": {
                "file_count": {
                    "value": 1,
                    "modifier": "GREATER_THAN"
                },
                "tags": {
                    "value": tagIds,
                    "modifier": "EXCLUDES"
                }
            }
        }
        result = self.__callGraphQL(query, variables)
        scenes = []
        for scene in result["findScenes"]["scenes"]:
            for i, file in enumerate(scene["files"]):
                if i == 0:  # skip first ID
                    continue
                id = file["id"]
                path = file["path"]
                scenes.append((id, path))
        return scenes

    def sceneCreate(self, id):
        # Finds scenes with studio
        query = """
mutation SceneCreate($sceneCreateInput: SceneCreateInput!){
  sceneCreate(input: $sceneCreateInput){
    files {
      id
    }
  }
}
        """
        variables = {"sceneCreateInput": {
            "file_ids": id
        }
        }
        self.__callGraphQL(query, variables)
        return

    def split_merged_files(self):
        for tag in TAGS_EXCLUDE:
            tagresults = self.findTags(tag)
            results = self.findScenes(tagresults)
            for result in results:
                id = result
                for id in result:
                    self.sceneCreate(id)
                    self.debug(f"Scene Split Created: Scene Created ID: {id}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if len(sys.argv) > 2:
            STASH_URL = sys.argv[2]
            API_KEY = sys.argv[3]
        if sys.argv[1] == "setup":
            client = SplitWith(STASH_URL, API_KEY)
            client.setup_tags()
        elif sys.argv[1] == "split_all":
            client = SplitWith(STASH_URL, API_KEY)
            client.split_merged_files()
        elif sys.argv[1] == "remove_tags":
            client = SplitWith(STASH_URL, API_KEY)
            client.remove_tags()
        elif sys.argv[1] == "api":
            fragment = json.loads(sys.stdin.read())
            scheme = fragment["server_connection"]["Scheme"]
            port = fragment["server_connection"]["Port"]
            domain = "localhost"
            if "Domain" in fragment["server_connection"]:
                domain = fragment["server_connection"]["Domain"]
            if not domain:
                domain = 'localhost'
            url = scheme + "://" + domain + ":" + str(port) + "/graphql"

            client = SplitWith(STASH_URL, API_KEY)
            mode = fragment["args"]["mode"]
            client.debug("Mode: "+mode)
            if mode == "setup":
                client.setup_tags()
            elif mode == "split_all":
                client.split_merged_files()
            elif mode == "remove_tags":
                client.remove_tags()
    else:
        print("")
