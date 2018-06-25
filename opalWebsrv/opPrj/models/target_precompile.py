import os
currentSubsystem=os.path.basename(os.environ['TargetWorkingPath'].rstrip('/'))
if currentSubsystem == "opalwebsrvexp_sm_ip_com" :
	os.system("make -f AsyncIP.mk")
