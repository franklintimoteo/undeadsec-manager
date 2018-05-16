import logging
import sys
import os
from collections import namedtuple

import requests
from bs4 import BeautifulSoup

from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.widgets import Layout, Background, Frame, Label, Button, Divider, ListBox, Text, Widget, PopUpDialog, \
    MultiColumnListBox, Widget
from asciimatics.effects import Print
from asciimatics.renderers import FigletText
from asciimatics.event import KeyboardEvent
from asciimatics.exceptions import StopApplication, NextScene


logger = logging.getLogger("manager")

class Model:
    def __init__(self):
        self.Repository = namedtuple("Repository", "name description fullurl requirements")
        self.repositories = {} #{"hash": namedtuple}
        self.current_repo = None
        
    def _search_repos(self) -> None:
        """
        return: Repository("name", "description", "fullurl, ('requirements 01', 'requirementes 02')")
        """
        url = "https://github.com/UndeadSec?utf8=%E2%9C%93&q=&type=&language=python"
        response = requests.get(url)
        bsobj = BeautifulSoup(response.content, "html.parser")
        repos = bsobj.find_all("a", attrs={"itemprop": "name codeRepository"}) # type list
        repos = [repo.text.strip() for repo in repos]

        repos_descriptions = bsobj.find_all("p", attrs={"itemprop": "description"})
        repos_descriptions = [description.text.strip() for description in repos_descriptions[1:]] # o primeiro é irrelevante, pois e a descrição do usuário
        
        logger.debug("Repos: %s", repos)
        logger.debug("Repos descriptions: %s", repos_descriptions)
        
        _domain = "https://github.com/UndeadSec/{}/"
        for name, description in zip(repos, repos_descriptions):
            requirements = self._search_requirements(name)
            repo = self.Repository(name=name,
                                description=description,
                                fullurl=_domain.format(name),
                                requirements=tuple(requirements))
            self.repositories[hash(repo)] = repo

    def get_repositories(self):
        if not self.repositories:
            self._search_repos() # load repositories
        logger.debug("Returning repositories %s", self.repositories.values())
        return self.repositories.values()
    
    def get_repo(self, hashid):
        return self.repositories[hashid]
        
    def _search_requirements(self, repo_name: str) -> list:
        """
        return: ["requests", "third-lib", "urllib3"]
        """
        url = "https://raw.githubusercontent.com/UndeadSec/{}/master/requirements.txt".format(repo_name)
        response = requests.get(url)
        return [] if response.status_code != 200 else response.text.splitlines()
        
    def set_current_repo(self, hash_id):
        self.current_repo = hash_id
        
    def get_current_repo(self):
        return self.current_repo
        
class ReposView(Frame):
    def __init__(self, screen, model):      
        super().__init__(screen,
                        screen.height * 2 // 3,
                        screen.width * 2 // 3,
                        on_load=self._load_repos,
                        title="UNDEADSEC Tool Manager",
                        )
        self._model = model
        self._create_layouts()

    def _create_layouts(self):
        top_layout = Layout([100], fill_frame=True)
        self.add_layout(top_layout)
        self._list_box = ListBox(self.screen.height * 2 // 3 - 4, [], name="packages")
        top_layout.add_widget(self._list_box)

        bottom_layout = Layout([20, 60, 20], fill_frame=False)
        self.add_layout(bottom_layout)
        bottom_layout.add_widget(Button("Exit", self._exit))
        bottom_layout.add_widget(Button("More", self._more), 2)
        self.fix()

    def _load_repos(self):
        repositories = self._model.get_repositories()
        repositories = [(repo.name, hash(repo)) for repo in repositories]
        self._list_box.options = repositories
        logger.debug("Repositories: %s", repositories)
        logger.debug("Current options: %s", self._list_box.options)
            
    def _more(self):
        self.save()
        hash_id = self.data['packages']
        self._model.set_current_repo(hash_id)
        logger.debug("Getting package: %d", hash_id)
        raise NextScene("inforepo")

    def _exit(self):
        raise StopApplication("Bye!")


class InfoRepo(Frame):
    def __init__(self, screen, model):
        super().__init__(screen,
            screen.height * 2 // 3, 
            screen.width * 2 // 3,
            on_load=self._load_repo
            )

        self._model = model
        self._create_layouts()
        
    def _create_layouts(self):
        top_layout = Layout([10,10,50], fill_frame=True)
        self.add_layout(top_layout)
        top_layout.add_widget(Label("Nome"))
        
        self.label_name = Label("")
        top_layout.add_widget(self.label_name, 2)
        
        top_layout.add_widget(Label("URL"))
        
        self.label_fullurl = Label("")
        top_layout.add_widget(self.label_fullurl, 2)
        
        top_layout.add_widget(Label("Descrição"))
        self.label_description = Label("")
        top_layout.add_widget(self.label_description, 2)
        
        bottom_layout = Layout([20, 60, 20])
        self.add_layout(bottom_layout)
        self.label_downloading = Label("[-]")
        bottom_layout.add_widget(Button("Cancel", self._cancel))
        bottom_layout.add_widget(self.label_downloading, 1)
        bottom_layout.add_widget(Button("Download", self._download), 2)
        self.fix()
        
    def _load_repo(self):
        # TODO: fazer com que o que seja retornado seja de fato uma isntancia de Repository
        hash_id = self._model.get_current_repo()
        self.repo = self._model.get_repo(hash_id)
        self.label_name.text = self.repo.name
        self.label_fullurl.text = self.repo.fullurl
        self.label_description.text = self.repo.description
        self.label_downloading.text = "[-]"

    def _cancel(self):
        raise NextScene("repoview")
    
    def _download(self):
        fullurl = self.repo.fullurl
        fullurl = os.path.join(fullurl, "archive/master.zip")
        response = requests.get(fullurl, stream=True)
        file_name = "{}-master.zip".format(self.repo.name)

        with open(file_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=128):
                f.write(chunk)
        self.label_downloading.text = "[Download completed!]"
        
model = Model()
def main(screen):
    scenes = [
        Scene([ReposView(screen, model)], name="repoview"),
        Scene([InfoRepo(screen, model)], name="inforepo"),
    ]
    screen.play(scenes)

if __name__ == "__main__":
    fmt = logging.Formatter("%(levelname)s %(name)s %(funcName)s %(message)s")
    std_handler = logging.StreamHandler(sys.stderr)
    std_handler.setFormatter(fmt)
    std_handler.setLevel(logging.DEBUG)
    # logger.addHandler(std_handler)

    file_name = "debug.log"
    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(fmt)
    #logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    logger.info("Executando script!")

    logging.basicConfig(level=logging.DEBUG,
                        filename=file_name,
                        format="%(levelname)s %(name)s %(funcName)s %(message)s")

    Screen.wrapper(main)