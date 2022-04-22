# PyRef


## Description
PyRef is a tool that automatically detect mainly method-level refactoring operations in Python projects.

Current supported refactoring operations:
* Rename Method
* Add Parameter
* Remove Parameter
* Change/Rename Parameter
* Extract Method
* Inline Method
* Move Method
* Pull Up Method
* Push Down Method

## Usage

Clone a repository from GitHub using PyRef:

```sh
python3 main.py repoClone -u "username" -r "Repo Name"
```

You can also use git command to clone the repository.

Extract refactorings from a given repository

```sh
python3 main.py getrefs -r "[PATH_TO_REPOSITORY]"
```

You can also use flag *-s* to skip the commit which takes more than N minutes to extract the refactorings. For example, the following command skips commits which were processed for more than 10 minutes:

```sh
python3 main.py getrefs -r "[PATH_TO_REPOSITORY]" -s 10 
```

If you want to look into specific commit, you can use flag *-c*.
If you want to look into specific directory, you can use flag *-d*.

```sh
python3 main.py getrefs -r "[PATH_TO_REPOSITORY]" -c "[CommitHash]" -d "[Directory]"
```

The detected refactorings will be recorded in the current folder as a json file "[project]_data.json".

## Play with PyRef
You will need to first install the third-party dependencies. You can use the following command in the folder of PyRef:

```sh
pip3 install -r requirements.txt
```

We provide a toy project for you to test PyRef, which can be found at https://github.com/PyRef/DummyRef
Please execute the following commands in order:

```sh
python3 main.py repoClone -u "PyRef" -r "DummyRef"
python3 main.py getrefs -r "Repos/DummyRef"
```

The detected refactorings can be found in the file "DummyRef_data.json"

## Dataset for the Paper

This tool was part of the following study:

H. Atwi, B. Lin, N. Tsantalis, Y. Kashiwa, Y. Kamei, N. Ubayashi, G. Bavota and M. Lanza, "PyRef: Refactoring Detection in Python Projects," 2021 IEEE 21st International Working Conference on Source Code Analysis and Manipulation (SCAM), 2021, accepted.

The labeled oracle used in the paper can be found in the file "data/dataset.csv".
