import socket
import select
import sys
import time
import random

user_ID = 0
final = {}
entry = []

def print_table(table):
    ''' Prints the routing table based on the database'''
    sortedID = sorted(table.keys())
    print("_______________User Router ID: {0}_____________".format(user_ID))
    print("_______________________________________________")
    print(" ID |First|Cost|Grbg Flag|Drop t.out|Grbg t.out|")
    print("____|_____|____|_________|__________|__________")
    for i in range(0, len(table)):
        info = table[sortedID[i]]
        cost = info[1]
        if info[2] == True:
            cost = 16
        print(" {:>2} |".format(sortedID[i]), end='')
        print(" {:>3} | {:>2} | {:<7} | {:<8} | {:<8} |" .format(info[0], cost, info[2], str(info[3][0])[:7], str(info[3][1])[:7]))
        print("_______________________________________________")

def get_table(file_name):
    '''Read config file '''
    global user_ID
    total = []
    table = {}
    file = open(file_name, 'r')
    for line in file.readlines():
        l = line.split(',')
        total.append(l)
        user_ID = int(total[0][1])
    for i in range(1, len(total[1])):
        entry.append(int(total[1][i]))
    for i in range(1, len(total[2])):
        origin = total[2][i]
        origin = origin.split('-')
        router = int(origin[2])
        port = int(origin[0])
        final[port] = router
        first_router = router
        metric = int(origin[-2])
        flag = False
        timers = [0, 0]
        select = [first_router, metric, flag, timers]
        table[router] = select
    return table

def go_firsthop(first_entry, table):
    ''' Returns a list of routers use 'first_entry' as the first hop'''
    routers = []
    for router in sorted(table.keys()):
        if table[router][0] == first_entry:
            routers.append(router)
    return routers

def get_listen_list():
    '''bind the socket and put into a list'''
    ret = []
    for i in range(0, len(entry)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', int(entry[i])))
        ret.append(sock)
    return ret

def iD_List(rec_id, table):
    '''Checks whether or not the given router_id exists in the routing table '''
    keys = []
    if table is not None:
        keys = table.keys()
    return True if rec_id in keys else False

def send_packet(table):
    '''create and sends an update packet'''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in final:
        keys = []
        if table is not None:
            keys = table.keys()
        text = "2" + ',' + "2" + ',' + str(user_ID) # command/version
        result = text
        for i in keys:
            value = table[i]
            result += ',' + str(i) + ','
            metric = str(value[1]) if i not in table.values() else 16
            result += metric
        sock.sendto(result.encode('utf-8'), ("127.0.0.1", port))

def receiver(table, timeout, socket_list):
    '''Checks the sockets to see if any messages have been received.'''
    current = table
    list_fir, list_emp, list_emp = select.select(socket_list, [], [], timeout)
    if list_fir:
        # strip the data from receive 
        data, addr = list_fir[0].recvfrom(256)
        data = str(data).replace("b", "").replace("'", "")
        data = data.split(',')
        src = int(data[2])
        # reset timers for direct neighbour
        current[src][-1][0] = 0
        current[src][-1][1] = 0
        current[src][2] = False
        index = 3 # skip the header
        
        while index < len(data):
            rec_id = int(data[index])
            router_id = int(data[index])
            metric = min(int(data[index + 1]) + current[src][1], 16)
            if router_id not in final.values() and router_id != user_ID:
                if not iD_List(rec_id, table):
                    current[router_id] = [src, metric, False, [0, 0]]
                if metric < current[router_id][1]:
                    table[router_id][1] = metric
                    table[router_id][0] = src
                if src == current[router_id][0]:
                    current[router_id][1] = metric
                    current[router_id][0] = src
                    current[router_id][-1][0] = 0  
                    current[router_id][-1][1] = 0
                    current[router_id][2] = False
            index += 2 # next index and skip the cost
    return table

def setTimer(table, time):
    '''Adds time onto all routing table entry timers.'''
    cut_off_time = 30
    gc_timeout = 30
    for key, value in sorted(table.items()):
        if value[2]:
            value[-1][1] += time
            if value[-1][1] > gc_timeout:
                del table[key] # remove unreachable router
        else:
            value[-1][0] += time
            if value[-1][0] > cut_off_time:
                value[2] = True
                
if __name__ == "__main__":
    args_num = len(sys.argv)
    if args_num == 2: # pass input check
        table = get_table(sys.argv[1]) # generate the table and metric in case reconnect within 30s
        socket_list = get_listen_list()
        while True:
            track = time.time()
            connect_time = 0
            increase = 0
            while connect_time < 0.3:
                table = receiver(table, 0.3, socket_list)
                increase = time.time() - track
                track = time.time()
                setTimer(table, increase)
                connect_time += increase
            print_table(table)
            send_packet(table)
