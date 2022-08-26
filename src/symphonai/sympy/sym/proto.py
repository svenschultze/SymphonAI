from asyncio import protocols
import os
from glob import glob
import grpc
from glob import glob
import sys
sys.path.append('/build')

class Servicer():
    def __init__(self, protofile, node=os.getenv("SYMNAME")):
        self.node = node
        self.protofile = protofile
        print(protofile)
        print(os.getcwd())
        self.protos, self.services = grpc.protos_and_services(f"{node}/proto/{protofile}")
        self.service_calls = dict()

    def get_service(self, name):
        return self.protos.DESCRIPTOR.services_by_name[name]

    def has_service(self, name):
        for srvs in self.protos.DESCRIPTOR.services_by_name:
            print(srvs)
        return name in self.protos.DESCRIPTOR.services_by_name

    def get_method(self, service, name):
        return service.methods_by_name[name]

    def has_method(self, service, name):
        return name in service.methods_by_name

    def add_to_server(self, server):
        for name in self.protos.DESCRIPTOR.services_by_name:
            getattr(self.services, f"add_{name}Servicer_to_server")(self.create(name), server)

    def create(self, service_name):
        obj = getattr(self.services, f"{service_name}Servicer")()
        print(dir(obj))
        return obj

    def add_call(self, service_name, call_name, call):
        servicer_class = getattr(self.services, f"{service_name}Servicer")
        setattr(servicer_class, call_name, call)

    def request(self, service_name, method_name, request, channel):
        service =  getattr(self.services, f"{service_name}")
        method = getattr(service, method_name)
        
        return method(request, f'{self.node}:50051', insecure=True)

    def get_input_type(self, service, method):
        s = self.get_service(service)
        m = self.get_method(s, method)
        type_descriptor = m.input_type
        return getattr(self.protos, type_descriptor.name)

    def get_output_type(self, service, method):
        s = self.get_service(service)
        m = self.get_method(s, method)
        type_descriptor = m.output_type
        return getattr(self.protos, type_descriptor.name)

def get_protos():
    save_cwd = os.getcwd()
    os.chdir("/build")

    nodes = dict()
    for node in os.listdir():
        nodes[node] = []
        if not os.path.exists(f"/build/{node}/proto"):
            continue
        os.chdir(f"/build/{node}/proto")
        for protofile in os.listdir():
            print(protofile, node)
            nodes[node].append(Servicer(protofile, node))
            
    os.chdir(save_cwd)

    return nodes