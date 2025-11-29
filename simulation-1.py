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

    assert bob.pop_data("mount") == "everest"
    assert ema.get_data("mount") == None

    charlie.put_data({"date": "yesterday"})
    assert dan.get_data("date") == "yesterday"

    assert hannah.get_data("date") == None
    connect_all([bob, gorge])
    connect_all([ema, igris])

    gorge.sync_up() # Initiate a syncup routine

    assert igris.get_data("date") == "yesterday"
    assert hannah.pop_data("weather") == "sunny"
    assert igris.get_data("weather") == None


    pass

if __name__ == "__main__":
    main()