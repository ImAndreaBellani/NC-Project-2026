import sys
import random
import math
import heapq
from optparse import OptionParser
from custom_rand import CustomRand

class Flow:
	def __init__(self, src, dst, size, t):
		self.src, self.dst, self.size, self.t = src, dst, size, t
	def __str__(self):
		return "%d %d 3 100 %d %.9f"%(self.src, self.dst, self.size, self.t)

def translate_bandwidth(b):
	if b == None:
		return None
	if type(b)!=str:
		return None
	if b[-1] == 'G':
		return float(b[:-1])*1e9
	if b[-1] == 'M':
		return float(b[:-1])*1e6
	if b[-1] == 'K':
		return float(b[:-1])*1e3
	return float(b)

def poisson(lam):
	return -math.log(1-random.random())*lam

if __name__ == "__main__":
	port = 80
	parser = OptionParser()
	parser.add_option("-c", "--cdf", dest = "cdf_file", help = "the file of the traffic size cdf", default = "uniform_distribution.txt")
	parser.add_option("-n", "--nhost", dest = "nhost", help = "number of hosts")
	parser.add_option("-l", "--load", dest = "load", help = "the percentage of the traffic load to the network capacity, by default 0.3", default = "0.3")
	parser.add_option("-b", "--bandwidth", dest = "bandwidth", help = "the bandwidth of host link (G/M/K), by default 10G", default = "10G")
	parser.add_option("-t", "--time", dest = "time", help = "the total run time (s), by default 10", default = "10")
	parser.add_option("-o", "--output", dest = "output", help = "the output file", default = "tmp_traffic.txt")
	parser.add_option("-i", "--incast", dest = "incast", help = "enable incast traffic", default = 0)
	parser.add_option("-p", "--incastpercentage", dest = "incastpercentage", help = "the percentage of incast traffic, by default 2", default = "2")
	options,args = parser.parse_args()

	base_t = 2000000000

	if not options.nhost:
		print "please use -n to enter number of hosts"
		sys.exit(0)
	nhost = int(options.nhost)
	incast_enabled = bool(options.incast)
	incast_percentage = float(options.incastpercentage)/100
	load = float(options.load)
	bandwidth = translate_bandwidth(options.bandwidth)
	time = float(options.time)*1e9 # translates to ns
	output = options.output
	if bandwidth == None:
		print "bandwidth format incorrect"
		sys.exit(0)

	fileName = options.cdf_file
	file = open(fileName,"r")
	lines = file.readlines()
	# read the cdf, save in cdf as [[x_i, cdf_i] ...]
	cdf = []
	for line in lines:
		x,y = map(float, line.strip().split(' '))
		cdf.append([x,y])
	
	# create a custom random generator, which takes a cdf, and generate number according to the cdf
	customRand = CustomRand()
	if not customRand.setCdf(cdf):
		print "Error: Not valid cdf"
		sys.exit(0)
	if incast_enabled:
		output=(fileName[0:5]).lower()+"_L"+str(int(load*100))+"_T"+str(options.time)+"_I"+str(options.incastpercentage)+".txt"
	else:
		output=(fileName[0:5]).lower()+"_L"+str(int(load*100))+"_T"+str(options.time)+".txt"
	ofile = open(output, "w")
	print("output file: %s"%output)
	# generate flows
	avg = customRand.getAvg()
	avg_inter_arrival = 1/(bandwidth*load/8./avg)*1000000000
	n_flow_estimate = int(time / avg_inter_arrival * nhost)
	print("n_flow_interarrival %d"%n_flow_estimate)

	n_flow = 0
	ofile.write("%d \n"%n_flow_estimate)
	host_list = [(base_t + int(poisson(avg_inter_arrival)), i) for i in range(nhost)]
	all_flows=[]
	heapq.heapify(host_list)
	while len(host_list) > 0:
		t,src = host_list[0]
		if (t > time + base_t):
			heapq.heappop(host_list)
			continue
		inter_t = int(poisson(avg_inter_arrival))
		new_tuple = (src, t + inter_t)
		dst = random.randint(0, nhost-1)
		while (dst == src):
			dst = random.randint(0, nhost-1)
	
		size = int(customRand.rand())
		if size <= 0:
			size = 1
		n_flow += 1;
		all_flows.append((t, src, dst, size))
		if (t + inter_t < time + base_t):
			heapq.heapreplace(host_list, (t + inter_t, src))	
		else:
			heapq.heappop(host_list)
	if incast_enabled:
		avg_inter_incast= 1/(bandwidth*nhost*incast_percentage/8/(500000*60))*1000000000*nhost
		print("incast_percentage: %f"%(float(incast_percentage)))
		print("interincast:%d"%(int(time /avg_inter_incast)))
		print("interincast adjusted for rack:%d"%(int(time /avg_inter_incast*nhost)))
		n_flow_estimate = int(time / avg_inter_arrival * nhost)+ int(time/avg_inter_incast *nhost*60)
		print("n_flow_estimate: %d"%n_flow_estimate)
		incast_list = [(base_t + int(poisson(avg_inter_incast)), i) for i in range(nhost)]
		heapq.heapify(incast_list)
		while len(incast_list) > 0:
			t,dst = incast_list[0]
			if(t > time + base_t):
				heapq.heappop(incast_list)
				continue
			inter_t = int(poisson(avg_inter_incast))
			new_tuple = (dst, t + inter_t)
			
			srclist=[]
			for i in range(0, 60):
				new_tuple = (dst, t + inter_t)
				src = random.randint(0, nhost-1)
				while (dst == src or src in srclist):
					src = random.randint(0, nhost-1)
				srclist.append(src)
				n_flow += 1;
				all_flows.append((t, src, dst, 500000))
			if (t + inter_t > time + base_t):
				heapq.heappop(incast_list)
			else:
				heapq.heapreplace(incast_list, (t + inter_t, dst))

	all_flows.sort(key = lambda x: x[0])
	for f in all_flows:
		ofile.write("%d %d 3 100 %d %.9f\n"%(f[1], f[2], f[3], f[0] * 1e-9))
	ofile.seek(0)
	ofile.write("%d"%n_flow)
	ofile.close()

'''
	f_list = []
	avg = customRand.getAvg()
	avg_inter_arrival = 1/(bandwidth*load/8./avg)*1000000000
	# print avg_inter_arrival
	for i in range(nhost):
		t = base_t
		while True:
			inter_t = int(poisson(avg_inter_arrival))
			t += inter_t
			dst = random.randint(0, nhost-1)
			while (dst == i):
				dst = random.randint(0, nhost-1)
			if (t > time + base_t):
				break
			size = int(customRand.rand())
			if size <= 0:
				size = 1
			f_list.append(Flow(i, dst, size, t * 1e-9))

	f_list.sort(key = lambda x: x.t)

	print len(f_list)
	for f in f_list:
		print f
'''
