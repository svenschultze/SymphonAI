import os
from symphonai import docker
import shutil
import json
import yaml

symdir = "/".join(__file__.split("/")[:-2])
currentdir = os.getcwd().split('/')[-1]

def setup(args):
    os.makedirs(".sym", exist_ok=True)
    os.makedirs("env", exist_ok=True)
    os.makedirs("src", exist_ok=True)

    open("global.env", "w").close()

    docker.build_mosquitto()
    docker.build_nginx()

def create(args):
    print("Creating package", args.name, "with env", args.env)

    pkg_dir = f"src/{args.name}"
    if os.path.exists(pkg_dir):
        print(f"Package of name {args.name} already exists")
        return

    if not os.path.exists(f"env/{args.env}"):
        print(f"Env {args.env} does not exist. Creating from default env")
        shutil.copy(f"{symdir}/envs/default", f"env/{args.env}")

    shutil.copytree(f"{symdir}/template", f"{pkg_dir}")

    with open(f"{pkg_dir}/config.json", "w") as f:
        json.dump({
            "env": args.env,
            "options": {},
        }, f, indent=4)

def build(args):
    for dockerfile in os.listdir("env"):
        docker.build(dockerfile)

    pkgs = {}
    for pkg in os.listdir("src"):
        pkgs[pkg] = json.load(open(f"src/{pkg}/config.json"))

    services = dict()
    for pkg, config in pkgs.items():
        services[pkg] = config["options"]
        services[pkg].update({
            "image": f"sym/{currentdir}:{config['env']}",
            "volumes": [f"{os.getcwd()}/src/{pkg}:/node"],
            "networks": [currentdir],
            "depends_on": ["mosquitto"],
            "env_file": [f"{os.getcwd()}/global.env", f"{os.getcwd()}/src/{pkg}/params.env"],
        })

    services["mosquitto"] = {
        "image": "symphonai/mosquitto",
        "networks": [currentdir],
    }

    with open(".sym/docker-compose.yml", "w") as f:
        yaml.dump({
            "version": "3.7",
            "services": services,
            "networks": {
                currentdir: {
                    "driver": "bridge",
                },
            }
        }, f)

def run(args): 
    os.system("docker compose -f .sym/docker-compose.yml up --remove-orphans")