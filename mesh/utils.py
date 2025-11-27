def connect_all(node_lists: list):
    for node_a in node_lists:
        for node_b in node_lists:
            if node_a != node_b:
                node_a.connect(node_b)
                node_b.connect(node_a)


def is_A_greater_than_B(A, B):
    '''
    Returns elements from list A that list B does not have.
    '''

    for element in A:
        if element not in B:
            yield element
        
    return []

def A_minus_B(A, B):
    '''
    Returns elements from dict a that dict B does not have.
    '''
    for element, value in A.items():
        if element not in B:
            yield (element, value)
        
    return {}
