# -*- coding: utf-8 -*-

from pygit2 import Keypair, RemoteCallbacks, Repository, clone_repository
from pygit2 import GIT_SORT_REVERSE
from .data import Frame
from abc import ABCMeta, abstractmethod
import re


class Git(object):
    def __init__(self, public_key, private_key, repo_from=None, repo_to=None):
        self.public_key = public_key
        self.private_key = private_key
        self.frame = Frame()

    def clone_repo(self, repo_from, repo_to):
        self.repo_from = repo_from
        self.repo_to = repo_to
        keypair = Keypair("git", self.public_key, self.private_key, "")
        callbacks = RemoteCallbacks(credentials=keypair)

        clone_repository(self.repo_from, self.repo_to, callbacks=callbacks)

    def traverse(self):
        repo = Repository('%s/.git' % self.repo_to)
        populator = FramePopulator(self.frame)

        generator_expression = (
            commit for commit in repo.walk(
                repo.head.target,
                GIT_SORT_REVERSE) if not re.match(
                    r'^merge', commit.message, re.IGNORECASE))

        for commit in generator_expression:
            populator.add_commit_to_lists(commit)

        populator.to_frame()

    @property
    def dataset(self):
        return self.frame


class TransformInterface(object, metaclass=ABCMeta):

    @abstractmethod
    def convert(self, value: str) -> str:
        pass


class AuthorTransform(TransformInterface):

    def convert(self, value: str) -> str:
        return value.name


class FramePopulator(object):
    def __init__(self, frame):
        self.lists = {}
        self.frame = frame
        self.variables = ['commit_id', 'commit_message', 'commit_author', 'is_bug']
        for variable in self.variables:
            self.lists[variable] = []

    def add_commit_to_lists(self, commit):
        for variable in self.variables:
            key = self.extract_key(variable)
            if variable.startswith('commit') and  self.create_transform_classname(key) in globals():
                value = self.transform(key, getattr(commit, key))
            else:
                value = ""
            self.lists[variable].append(value)

    def to_frame(self):
        for variable in self.variables:
            self.frame.add_column(variable, self.lists[variable])

    def extract_key(self, index):
        return index.split('_', maxsplit=1)[1]

    def create_transform_classname(self, value: str) -> str:
        return "%sTransform" % value.title()

    def transform(self, class_key: str, value: str) -> TransformInterface:
        class_name = self.create_transform_classname(class_key)
        object = globals()[class_name]
        return object().convert(value)
