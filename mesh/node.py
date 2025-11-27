from .utils import is_A_greater_than_B, A_minus_B

class Node:
    def __init__(self, name = None, connected_to: list | None = None):
        self.name = name
        self.connections = connected_to if connected_to else []
        self.data = {}

    def __call__(self, *args, **kwds):
        pass

    def __repr__(self):
        return f"<Node {self.name} connected_with({', '.join([n.name for n in self.connections])})>"


    # Network simulation functions
    def connect(self, node):
        if not node in self.connections:
            self.connections.append(node)
            node.connect(self)

        return len(self.connections)
    
    def disconnect(self, node):
        if node in self.connections:
            self.connections.remove(node)
            node.disconnect(self)
        return len(self.connections)

    def send(self, node, data):
        return node.recv(self, data)

    def recv(self, node, data):
        self.sync_up_recv(node, data)
        # raise NotImplementedError()


    # Data functions
    def put_data(self, key_value_pairs):
        for key, value in key_value_pairs.items():
            if key not in self.data:
                self.data[key] = value
            else:
                raise NotImplementedError()

        self.sync_up()

    def get_data(self, key):
        self.sync_up()

        return self.data.get(key)

    def pop_data(self, key):
        if key in self.data:
            _value = self.data.pop(key)
            self.sync_up() # BUG: This will re-populate the key in the data, as a form of self healing
            return _value

        raise NotImplementedError()

    def sync_up(self, nodes_list = None):
        if not nodes_list:
            nodes_list = self.connections

        for node in nodes_list:
            self.send(node, self.data)
    
    def sync_up_recv(self, sender, incoming_data):
        my_data = list(self.data.keys())
        in_data = list(incoming_data.keys())

        if my_data == in_data:
            # The the data is equivalent
            return

        P = self.connections.copy() # List of nodes to propagate the data to...        
        # P.remove(self) # No need to rebroadcast to self
        P.remove(sender) # No need to rebroadcast to the sender node

        if diff := dict(A_minus_B( incoming_data, self.data )):
            # Incoming data has updates
            self.data.update(diff)

        if dict(A_minus_B( self.data, incoming_data )):
            # The the data is equivalent
            P.append(sender)

        self.sync_up(P)

