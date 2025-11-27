from mesh.node import Node
from mesh.utils import connect_all

def main():
    alice = Node(name = "alice")
    bob = Node(name = "bob")
    charlie = Node(name = "charlie")
    dan = Node(name = "dan")
    ema = Node(name = "ema")

    fargo = Node(name = "fargo")
    gorge = Node(name = "gorge")
    hannah = Node(name = "hannah")
    
    igris = Node(name = "igris")
    john = Node(name = "john")

    connect_all([alice, bob, charlie, dan, ema])
    connect_all([fargo, gorge, hannah])
    connect_all([igris, john])

    alice.put_data({"hello": "world"})
    alice.put_data({"weather": "sunny"})
    alice.put_data({"date": "today"})
    bob.put_data({"mount": "everest"})
    bob.pop_data("mount")
    # charlie.put_data({"date": "yesterday"})
    
    # alice.get_data("")
    # dan.get_data("")
    

    pass

if __name__ == "__main__":
    main()