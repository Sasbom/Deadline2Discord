import socket
from Deadline.DeadlineConnect import DeadlineCon as Connect

con = Connect(socket.gethostname(),8081)
print(con.Pools.GetPoolNames())