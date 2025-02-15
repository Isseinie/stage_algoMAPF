#from pysat.solvers import Solver
import numpy as np
import math
import igraph
from copy import deepcopy
import heapq
from numpy import random
import priorityqueue


nb_recursion = 10
nb_attemps = 5

#G_M is the graph of movement & G_C of connection
#sources:list 
#targets:list (agent a goes from sources[a] to targets[a])
#exec: list of paths for each agent


def decoupled_exec(G_M, sources, targets) :
    '''algo shortest path for each agent : A*
    Output: execution (paths) or None if an agent has no path'''
    paths = []
    for a in range(0, len(sources)) :
       #pred_a = get_pred(G_M, sources[a], targets[a])
       pred_a = get_pred_Astar(G_M, sources[a], targets[a])
       if pred_a == None :
           return None
       else :
           paths.append(extract_path_from_pred(pred_a, sources[a], targets[a]))
    max_t = max(map(len, paths))
    for p in paths :
        while len(p) < max_t :
            p.append(p[len(p)-1]) #we want same-length paths for each agent, so we make them wait at their arrivals to complete their paths
    return paths

def extract_path_from_pred(pred, source, dest) :
    '''Get a path from the predecessor's array
    Input: pred array, source and destination vertices
    Output: path (list of vertices) '''
    if source == dest :
        return [source]
    else :
        return extract_path_from_pred(pred, source, pred[dest])+ [dest]


def get_pred(G_M, source, dest) :
    '''Simple algorithm which finds the predecessor's array using BFS
    Input: movement graph, source, destination
    Output: array of predecessors, None if there is no path between source and dest '''
    pred = [-1 for x in range(G_M.vcount())]
    queue = [source]
    visited = [False for x in range(G_M.vcount())]
    while len(queue) > 0 :
        x = queue.pop(0)
        visited[x] = True
        if x == dest :
            return pred
        neighbours = G_M.neighbors(x)
        for n in neighbours :
            if not(visited[n]) :
                queue.append(n)
                pred[n] = x
    return None

#A* path finding

def get_pred_Astar(G_M, source, dest):
    ''' A* algorithm with the heuristic 'shortest distance between the vertice and the destination'
    Input: movement graph, source, destination
    Output: array of predecessors, None if there is no path between source and dest '''
    pred = [-1 for x in range(G_M.vcount())]
    d = [-1 for x in range(G_M.vcount())]
    d[source]=0
    heap = priorityqueue.PriorityQueue(G_M.vcount())
    heap.push(source, get_distance(G_M, dest, source))
    visited = [False for x in range(G_M.vcount())]
    while not(heap.is_empty()) :
        x = heap.pop()
        visited[x] = True
        if x == dest :
            return pred
        neighbours = G_M.neighbors(x)
        for n in neighbours :
            if not(visited[n]) or d[n] > d[x] +1:
                d[n] = d[x] + 1
                heap.decrease(n, get_distance(G_M, dest, n)+d[n])
                pred[n] = x
    return None

def get_distance(G_M, goal, agent):
    ''' Compute the distance between the position of the agent and the goal'''
    xsource, ysource = G_M.vs[goal]["x_coord"], G_M.vs[goal]["y_coord"]
    xagent, yagent = G_M.vs[agent]["x_coord"], G_M.vs[agent]["y_coord"]
    return math.sqrt((xagent-xsource)**2 + (yagent-ysource)**2)


# Usefull functions

def nb_conflicts(exec, G_C) :
    '''Compute the number of connection conflicts found in the execution, by computing the number of configurations disconnected
    Input: execution exec(not None), communication graph G_C
    Output: int number of conflicts'''
    list_config = [[0 for i_a in range(len(exec))] for t in range(len(exec[0]))]
    for i_a in range(len(exec)) :
        for t in range(len(exec[i_a])):
            list_config[t][i_a] = exec[i_a][t]
    is_connected_array = map(lambda config : is_connected(config, G_C), list_config)
    return len(list(filter(lambda x : not x, is_connected_array)))
    

def is_connected(config, G_C):
    '''return True if the configuration is connected (it begins with a_0 and explores the neighbourhood. If an agent isn't visited, the configuration is disconnected)
    Input: configuration (list of position for each agent at time t), communication graph
    Output: boolean'''
    queue = [0]
    visited = [False for a in config]
    visited[0] = True
    while len(queue) > 0 :
        x = queue.pop()
        for i_a in range(0, len(config)):
            if G_C.are_connected(config[x], config[i_a]) or config[x] == config[i_a]: #on ne gère pas les collisions
                if not(visited[i_a]):
                    queue.append(i_a)
                    visited[i_a] = True
    return all(visited)




def is_ordered_connected(G_C, i, t, exec, middle): 
    '''Look in the list of neighbours of a_i at time t if there is a_j, j < i
    Input: Communication graph, id of a_i, time t, execution
    Output: true if a_i is connected to agents a_0... a_i-1 at time t in the execution exec'''
    if i == 0 :
        return True
    neighbours = G_C.neighbors(exec[i][t], mode = "all")
    for j in range(0, i):
        if middle[j] in neighbours:
            return True
    return False



def pick_time_with_conflict(exec, G_C) : 
    '''Choose t around the middle of the execution, with conflicts 
    Input: exec, communication graph
    Output: time t'''
    max_len = max(map(len, exec))
    for i in range(0,max_len//2):
        if nb_conflicts([[exec_i[max_len//2 + i]] for exec_i in exec], G_C) > 0 :
            return max_len//2 +i 
        elif nb_conflicts([[exec_i[max_len//2 - i]] for exec_i in exec], G_C) > 0 :
            return max_len//2 -i 
    if nb_conflicts([[exec_i[0]] for exec_i in exec], G_C) > 0:
        return 0
    if max_len%2==1 :
        if nb_conflicts([[exec_i[max_len-1]] for exec_i in exec], G_C) > 0:
            return max_len-1
    return max_len//2


def choose_order(G_C, config) :
    '''Choose an order of agents, by choosing the first randomly and the next by BFS
    Input: communication graph, initial configuration of agents
    Output: list of id '''
    i = np.random.randint(0, len(config), 1)[0]
    A_ordered_id = [i]
    #BFS on the initial configuration
    queue = G_C.neighbors(config[i], mode = "all")
    while len(A_ordered_id)<len(config) and len(queue)>0:
        v = queue.pop(0)
        for j in range(0, len(config)):
            if config[j]==v and not(j in A_ordered_id):
                A_ordered_id.append(j)
                queue += G_C.neighbors(config[j], mode = "all")
    if len(A_ordered_id)<len(config):
        return None
    else :
        return A_ordered_id


#do this with a priority queue
def execution_with_best_neighbour(G_M, G_C, sources, targets, i, t, middle):
    '''Choose a neighbour u of a_0...a_i-1 which minimize d(u, g_i) and nb of conflicts 
    Output: execution with a_i going through u at t'''
    Neighbours = []
    inside = [False for x in range(G_M.vcount())]
    # for j in range(0,i):
    #     Neighbours+= G_C.neighbors(middle[j], mode = "all") #réordonner ?
    #     Neighbours+= [middle[j]]
    for j in range(0, i):
        for v in G_C.neighbors(middle[j], mode = "all"):
            if not(inside[v]):
                Neighbours.append(v)
                inside[v]=True
        if not(inside[middle[j]]):
            Neighbours.append(middle[j])
            inside[middle[j]]=True
    best = Neighbours[0]
    best_exec = decoupled_exec(G_M, sources, targets)
    min_dist_u_goal = 2*len(best_exec[0])
    min_nb_conflicts = nb_conflicts(best_exec, G_C)
    min_len_exec = 2*len(best_exec)
    min_diff = 2*len(best_exec[0]) #t-min_dist_start_u
    #for u in Neighbours:
    for k in range(0,10):
        u = np.random.choice(Neighbours, 1)[0]
        exec_si_u = decoupled_exec(G_M, [sources[i]], [u])
        exec_u_gi = decoupled_exec(G_M, [u], [targets[i]])
        if exec_u_gi!= None and exec_si_u!= None:
            dist_start_u = len(exec_si_u[0])
            dist_u_gi = len(exec_u_gi[0])
            exec_first = decoupled_exec(G_M, sources, middle+[u])
            exec_second = decoupled_exec(G_M, middle+[u], targets)
            if exec_first!= None and exec_second!= None :
                exec_tested = concatanate_executions(exec_first,exec_second)
                if nb_conflicts(exec_tested, G_C) <= min_nb_conflicts:
                    if (np.abs(t-dist_start_u),dist_u_gi,len(exec_tested[0])) < (min_diff, min_dist_u_goal, min_len_exec):
                    #conditions en plus : np.abs(t-dist_start_u) < min_diff, len(exec_tested[0])<=min_len_exec ?
                        best = u
                        min_dist_u_goal = dist_u_gi
                        min_diff = np.abs(t-dist_start_u)
                        min_nb_conflicts = nb_conflicts(exec_tested, G_C)
                        best_exec = exec_tested
                        min_len_exec=len(exec_tested[0])
        #if there is one, then compute the distance d(u, g_i) and the nb of conflicts: 
        #if it's less than min_dist then and min_nb_conflicts then replace best by u
    return best, best_exec

def concatanate_executions(ex1, ex2):
    '''Input: 2 executions with same number of agents
    Output: the concatenation (in time) of the executions '''
    ex_final = deepcopy(ex1)
    for i_a in range(len(ex2)):
        ex_final[i_a]+= ex2[i_a][1:]
    return ex_final

###Algorithm (must return list of paths)

def mapf_algo(G_Mname, G_Cname, sources, targets):
    '''This algorithm's method is divide and conquer 
    Input: graphs names, lists of sources and targets
    Output: execution '''
    G_C = igraph.read(G_Cname)
    G_M = igraph.read(G_Mname)
    nb_it = 0
    while nb_it < nb_attemps : #number of attempts to find a better P
        #print("Attempt number ", nb_it+1)
        A_ordered_id = choose_order(G_C, sources)
        #print("Order of agents:", A_ordered_id) 
        #We reorder the sources and targets
        sources_ordered = [sources[i] for i in A_ordered_id]
        targets_ordered = [targets[i] for i in A_ordered_id]
        exec_changed = divide_and_conquer(sources_ordered, targets_ordered, G_C, G_M, nb_recursion) 
        if exec_changed!= None and nb_conflicts(exec_changed, G_C) == 0:
            return [exec_changed[A_ordered_id[i]] for i in range(len(sources))] #in the initial order
        else :
            nb_it+=1
    return None


def divide_and_conquer(sources, targets, G_C, G_M, n):
    '''This function fixes the connection problem around the middle of the execution, then does it again for each part
    Stops after 10 iterations'''
    exec = decoupled_exec(G_M, sources, targets)
    if exec == None or len(exec)==1:
        return exec
    #print("Call number ", nb_recursion+1-n, ":", exec)
    if nb_conflicts(exec, G_C) == 0 :
        #print("No conflict at call ", nb_recursion+1-n)
        return exec
    if n >0: #number of recursive calls = 10
        #print("nb conflicts = ", nb_conflicts(exec, G_C))
        t = pick_time_with_conflict(exec, G_C)
        #print(t)
        middle = [] #the new configuration at t
        for i in range(len(sources)):
            if is_ordered_connected(G_C, i, t, exec, middle) :
                middle.append(exec[i][t])
            else:
                u, exec_changed = execution_with_best_neighbour(G_M,G_C, sources[:i+1], targets[:i+1], i, t, middle) #update of exec_i
                if nb_conflicts(exec_changed, G_C) < nb_conflicts(exec[:i+1], G_C):
                    middle.append(u)
                else :
                    middle.append(exec[i][t])
        L1 =  divide_and_conquer(sources, middle, G_C, G_M, n-1) 
        L2 = divide_and_conquer(middle, targets, G_C, G_M, n-1)
        return concatanate_executions(L1, L2)
    else :
        return exec


###Algorithm : 2nd version 

def randomly_choose(start, goal, G_M, t):
    return random.randint(0, G_M.vcount(), 1)[0] #todo

def heuristic_compute(sources, targets, G_M, G_C, v, t, i, list_v_agents):
    random_agents = []
    for j in range(i+1, len(sources)):
        random_agents.append(randomly_choose(sources[j], targets[j], G_M, t))
    conflict = nb_conflicts([list_v_agents+[v]+random_agents], G_C)
    dist = len(decoupled_exec(G_M, [sources[i]], [v])[0]) + len(decoupled_exec(G_M, [v], [targets[i]])[0]) 
    '''dist = get_distance(G_M, v, sources[i])+ get_distance(G_M, targets[i], v) #todo
    for n in range(len(list_v_agents)):
        dist+= get_distance(G_M, list_v_agents[n], sources[n])+ get_distance(G_M, targets[n], list_v_agents[n])#todo'''
    return (dist, - conflict, v)


def search_vertices(sources, targets, t, G_M, G_C, list_v_agents):
    list_vertices = []
    heapq.heapify(list_vertices)
    if len(list_v_agents) >0 :
        neighbours = []
        for agent in list_v_agents :
            neighbours+= G_C.neighbors(agent, mode = 'all')
            neighbours.append(agent)
        for v in neighbours:
            if decoupled_exec(G_M, [sources[len(list_v_agents)]], [v]) != None and decoupled_exec(G_M, [v], [targets[len(list_v_agents)]])!= None :
                heapq.heappush(list_vertices, heuristic_compute(sources, targets, G_M, G_C, v, t, len(list_v_agents), list_v_agents))   
    else : 
        for v in range(G_M.vcount()):
            if decoupled_exec(G_M, [sources[len(list_v_agents)]], [v]) != None and decoupled_exec(G_M, [v], [targets[len(list_v_agents)]])!= None :
                heapq.heappush(list_vertices, heuristic_compute(sources, targets, G_M, G_C, v, t, len(list_v_agents), list_v_agents))
    return list_vertices

def recursive_func(sources, targets, G_C, G_M, t, list):
    print("List = ", list)
    if len(list) == len(sources):
        exec_first = decoupled_exec(G_M, sources, list)
        exec_second = decoupled_exec(G_M, list, targets)
        if exec_first!= None and exec_second!= None :
            exec_complete = concatanate_executions(exec_first, exec_second)
            return list, exec_complete
    else :
        vertices = search_vertices(sources, targets, t, G_M, G_C, list)
        print("possible vertices:", vertices)
        for v in vertices:
            list_final, exec = recursive_func(sources, targets, G_C, G_M, t, list+[v[2]])
            if exec!=None:
                if nb_conflicts(exec, G_C) == 0:
                    return list_final, exec #todo
        return None, None


def best_choice(sources, targets, G_C, G_M, n):
    exec = decoupled_exec(G_M, sources, targets)
    if exec == None or len(exec)==1:
        return exec
    print("Call number ", nb_recursion+1-n, ":", exec)
    if nb_conflicts(exec, G_C) == 0 :
        print("No conflict at call ", nb_recursion+1-n)
        return exec
    if n >0: #number of recursive calls = 10
        print("nb conflicts = ", nb_conflicts(exec, G_C))
        t = pick_time_with_conflict(exec, G_C)
        print("time", t)
        list, exec_changed = recursive_func(sources, targets, G_C, G_M, t, [])
        L1 =  best_choice(sources, list, G_C, G_M, n-1) 
        L2 = best_choice(list, targets, G_C, G_M, n-1)
        return concatanate_executions(L1, L2)
    else :
        return exec


###Tests

if __name__ == '__main__':
    G_comm = igraph.read("map1.png_comm_uniform_grid_1_range_6.graphml")
    G_mov = igraph.read("map1.png_phys_uniform_grid_1_range_6.graphml")

    print(G_mov.vcount())

    sources = [47, 14]
    targets = [55, 20]
    sources2 = [18, 10]
    targets2 = [58, 62]
    exec2 = decoupled_exec(G_mov, sources2, targets2)

    pred_ex = get_pred(G_mov, 47, 55)
    path_ex = extract_path_from_pred(pred_ex, 47, 55)

    exec_ex = decoupled_exec(G_mov, sources, targets)
    exec_ex[0][2] = 10
    print(exec_ex)

    print(nb_conflicts(exec_ex, G_comm))
    print(G_comm.are_connected(16,10))
    print(nb_conflicts([[16, 10]], G_comm))
    print(pick_time_with_conflict(exec_ex, G_comm))

    #print(concatanate_executions([[1,2,3], [4,5,6]], [[3,7,8],[6,9,10]]))

    #print(G_mov.vs[3]["x_coord"])






### Abandonned functions, algorithms


'''def last_is_disconnected(G_M, G_C, A, P):
    return False, 0

def find_path(G_M, G_C, A, n, constraints):
    return Solver()

def extract_exec(G_M, G_C, A, constraints):
    return 0

def pick_config(G_M, G_C, A, t):
    return [[0] for a in A]

def MAPF1(G_M, G_C, A) :
    constraints = []
    P = decoupled_exec(G_M, G_C, A)
    n = max([len(Pai) for Pai in P])
    while has_conflict(P):
        agent, t = pick_disconnected(G_M, G_C, A)
        constraints.append(is_connected(G_M, G_C, A, agent, t))
        while(find_path(G_M, G_C, A, n, constraints).solve() == False) :
            n+= 1
        P = extract_exec(G_M, G_C, A, constraints)
    return P

def MAPFmalin(G_M, G_C, A, final_state):
    constraints = []
    P = decoupled_exec(G_M, G_C, A)
    n = max([len(Pai) for Pai in P])
    if not(has_conflict(P)) :
        return P
    else :
        agent, t = pick_disconnected(G_M, G_C, A)
        constraints.append(is_connected(G_M, G_C, A, agent, t))
        while n < NMAX :
            while(find_path(G_M, G_C, A, n, constraints).solve() == False) :
                n+= 1
            P_extr = extract_exec(G_M, G_C, A, n, constraints)
            P_final = MAPFmalin(G_M, G_C, A, P_extr[-1]) + MAPFmalin(G_M, G_C, P_extr[-1], final_state)
            if not(has_conflict(P_final)) :
                return P_final
            else :
                constraints.append(pick_config(G_M, G_C, A, t) != P_extr[t])'''


'''def update(G_M, exec, u, i, t):
    ''update exec with a_i going through u at t''
    sources_first = [exec[0][j] for j in range(0, len(exec[0]))]
    targets_first = [exec[t][j] for j in range(0, len(exec[0]))]
    targets_first[i] = u
    sources_second = [exec[t][j] for j in range(0, len(exec[0]))]
    targets_second = [exec[len(exec)][j] for j in range(0, len(exec[0]))]
    sources_second[i] = u
    return decoupled_exec(G_M, sources_first, targets_first) + decoupled_exec(G_M, sources_second, targets_second)'''



'''def path_of_length(G_M, start, arrival, t):
    if t == 0 :
        if start == arrival : 
            return [arrival] 
        else : 
            return []
    else :
        Neighbours = G_M.neighbors(start, mode = "all")
        return [([n]+x for x in path_of_length(G_M, n, arrival, t-1)) for n in Neighbours]

def pick_path_of_length(G_M, start, arrival, t):
    paths = path_of_length(G_M, start, arrival, t)
    res = []
    for p in paths :
        if len(p) == t :
            res.append(p)
    return res'''

'''def execution_with_best_neighbour(G_M, G_C, sources, targets, i, t, exec):
    Choose a neighbour u of a_0...a_i-1 which minimize d(u, g_i) and nb of conflicts 
    Output: execution with a_i going through u at t
    Neighbours = []
    for j in range(0,i):
        Neighbours+= G_C.neighbors(exec[j][t], mode = "all") #réordonner ?
        Neighbours+= [exec[j][t]]
    best = Neighbours[0]
    best_exec = deepcopy(exec)
    min_dist_u_goal = 2*len(exec[0])
    min_nb_conflicts = nb_conflicts(exec, G_C)
    min_len_exec = 2*len(exec)
    #min_diff = 2*len(exec[0]) #t-min_dist_start_u
    for u in Neighbours:
        exec_si_u = decoupled_exec(G_M, [sources[i]], [u])
        exec_u_gi = decoupled_exec(G_M, [u], [targets[i]])
        if exec_u_gi!= None :
            dist_start_u = len(exec_si_u[0])
            dist_u_gi = len(exec_u_gi[0])
            sources_first = [sources[j] for j in range(len(sources))]
            targets_first = [exec[j][t] for j in range(len(sources))]
            targets_first[i] = u
            sources_second = [exec[j][t] for j in range(len(sources))]
            targets_second = [targets[j] for j in range(len(sources))]
            sources_second[i] = u
            exec_first = decoupled_exec(G_M, sources_first, targets_first)
            exec_second = decoupled_exec(G_M, sources_second, targets_second)
            if exec_first!= None and exec_second!= None :
                exec_tested = concatanate_executions(exec_first,exec_second)
                if nb_conflicts(exec_tested, G_C) < min_nb_conflicts:
                    if (dist_u_gi,len(exec_tested[0])) <= (min_dist_u_goal,min_len_exec):
                    #conditions en plus : np.abs(t-dist_start_u) < min_diff, len(exec_tested[0])<=min_len_exec ?
                        best = u
                        min_dist_u_goal = dist_u_gi
                        #min_diff = np.abs(t-dist_start_u)
                        min_nb_conflicts = nb_conflicts(exec_tested, G_C)
                        best_exec = exec_tested
                        min_len_exec=len(exec_tested[0])
        #if there is one, then compute the distance d(u, g_i) and the nb of conflicts: 
        #if it's less than min_dist then and min_nb_conflicts then replace best by u
    return best_exec, best'''

'''def divide_and_conquer(sources, targets, G_C, G_M, n):
    This function fixes the connection problem around the middle of the execution, then does it again for each part
    Stops after 10 iterations
    exec = decoupled_exec(G_M, sources, targets)
    if exec == None or len(exec)==1:
        return exec
    print("Call number ", nb_recursion+1-n, ":", exec)
    if nb_conflicts(exec, G_C) == 0 :
        print("No conflict at call ", nb_recursion+1-n)
        return exec
    if n >0: #number of recursive calls = 10
        print("nb conflicts = ", nb_conflicts(exec, G_C))
        t = pick_time_with_conflict(exec, G_C)
        print(t)
        for i in range(len(sources)):
            print("agent ", i, "is at", exec[i][t])
            if not(is_ordered_connected(G_C, i, t, exec)):
                exec_changed, u = execution_with_best_neighbour(G_M,G_C, sources[:i+1], targets[:i+1], i, t, exec) #update of exec_i
                print("for agent ", i, "is ", u)
                print(exec_changed)
                if nb_conflicts(exec_changed, G_C) < nb_conflicts(exec[:i+1], G_C):
                    exec[:i+1] = exec_changed
                    print("ok")
        L1 =  divide_and_conquer(sources, [exec_i[t] for exec_i in exec], G_C, G_M, n-1) 
        L2 = divide_and_conquer([exec_i[t] for exec_i in exec], targets, G_C, G_M, n-1)
        return concatanate_executions(L1, L2)
    else :
        return exec'''