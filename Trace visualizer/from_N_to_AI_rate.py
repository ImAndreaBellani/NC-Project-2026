import math

B = 100 # in Gbps
eta = 0.95
RTT = 12.240
if __name__ == "__main__":
    for N in range(1,200):
        ris = ((B*1000*(1-eta))/N)
        print("N = "+str(N)+ " => rate_AI [Mb/s] should be: "+str(math.trunc(ris)) + " (equivalent to W_AI [B] = " +str(math.trunc((ris*RTT)/8))+" assuming "+str(RTT)+" us of RTT)")
