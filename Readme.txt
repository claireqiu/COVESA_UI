Prerequists:
1. IoTDB is cleaned
2. information layer is running, knowledge layer is running
3. RemotiveLab recording is configured
4. pyhotn script is read

Step1:
Install all the packages in the requirment.txt

Step2:
Run the application:
streamlit run UI.py

optional:
clear cache:
streamlit cache clear

Step3:
Connect to websoket and subscribe to data FixPoints

Step4: 
load the origial rule set:driving_style_inference_rules.dlog

Step5:
1. Run the python script and Play remotivelab recording.

Step6:
check the reviced message about 40s later, the avg message is above 200.

step7:
Pause the remotivelab, update the driving_style_inference_rules_update.dlog

step8:
Contintue the play, at 2:43mins, the new message comes in with avg angle change above 100

