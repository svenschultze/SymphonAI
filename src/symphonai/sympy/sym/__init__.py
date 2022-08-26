import os
from platform import node
from sym.proto import get_protos

import json
def get_param(varname):
    try:
        return json.loads(os.getenv(varname))
    except:
        return os.getenv(varname)

nodes = dict()
#try:
nodes = get_protos()
#except Exception as e:
#    print("error getting protos")

node_name = os.getenv("SYMNAME")

#if node_name in nodes:
#    own_servicers = nodes[node_name]#
#
#    servicers = dict()

#    for servicer_name, servicer in own_servicers.items():
#        class Servicer(servicer["servicer"]):
#            def __init__(self):
#                super().__init__()
#                self._add_to_server = servicer["add_to_server"]
#        servicers[servicer_name] = Servicer()

used_servicers = []
def method(servicer_name):
    def decorator(m):
        service = None

        for servicer in nodes[node_name]:
            print(servicer)
            if servicer.has_service(servicer_name):
                service = servicer.get_service(servicer_name)
        if not service:
            raise NameError(f"Cannot find any methods of {servicer_name} on {node_name}")
        
        if not servicer.has_method(service, m.__name__):
            raise NameError(f"Cannot find method {m.__name__} of {servicer_name} on {node_name}")

        def call(self, request, context):
            kwargs = dict()
            for field, value in request.ListFields():
                kwargs[field.name] = value
            for servicer in nodes[node_name]:
                if servicer.has_service(servicer_name):
                    service = servicer.get_service(servicer_name)
                    method = service.get_method(m.__name__)
                    used_servicers.append(servicer)

                    return servicer.get_output_type(service.name, m.__name__)(**m(**kwargs))
        servicer.add_call(service.name, m.__name__, call)
        
        return m
    return decorator

channels = dict()
TIMEOUT_SEC = 15
def call(target, service_name, method_name):
    if target not in nodes:
        raise NameError(f"Cannot find any methods on {target}")
    
    node = nodes[target]

    service = None
    for servicer in node:
        if servicer.has_service(service_name):
            service = servicer.get_service(service_name)
    if not service:
        raise NameError(f"Cannot find any methods of {service_name} on {target}")
    
    if not servicer.has_method(service, method_name):
        raise NameError(f"Cannot find method {method_name} of {service_name} on {target}")

    method = servicer.get_method(service, method_name)


    def m(*args, **kwargs):
        if target not in channels:
            import grpc

            channels[target] = grpc.insecure_channel(f'{target}:50051')

            try:
                grpc.channel_ready_future(channels[target]).result(timeout=TIMEOUT_SEC)
                print("channel connected")
            except grpc.FutureTimeoutError:
                print("channel timed out")

        with channels[target] as channel:
            result = servicer.request(service_name, method_name, servicer.get_input_type(service_name, method_name)(*args, **kwargs), channel)

            ret = dict()
            for field, value in result.ListFields():
                ret[field.name] = value
            return ret

    return m

def serve(block=True):
    from concurrent import futures
    import grpc

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    import signal
    def stop():
        server.stop(1)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)

    for servicer in used_servicers:
        servicer.add_to_server(server)
    server.add_insecure_port('0.0.0.0:50051')
    server.start()
    if block:
        server.wait_for_termination()
