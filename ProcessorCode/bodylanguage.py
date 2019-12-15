#creds to Daniil-Osokin as this is largely taken from the demo for the pose estimation library

import sys
import requests
import cv2
import time
from time import sleep
import torch
import numpy as np

#importing pose estimation library stuffs
sys.path.insert(1, '../lightweight-human-pose-estimation.pytorch') #this points to the pose estimation library
from models.with_mobilenet import PoseEstimationWithMobileNet
from modules.keypoints import extract_keypoints, group_keypoints
from modules.load_state import load_state
from modules.pose import Pose, propagate_ids
from val import normalize, pad_width
from demo import infer_fast

#globals for for fps calculation
counter = 0
fpsTime = time.time()

#setup video stream (MJPG)
def setupCam(ip="192.168.43.111", port="8080"):
	cap = cv2.VideoCapture('http://{}:{}/?action=stream'.format(ip, port))
	return cap

#kill video stream
def killCam(cap):
	cap.release()

#receives video stream, computes fps, displays image
def getFrame(cap):
	global counter, fpsTime
	ret, frame = cap.read(cv2.IMREAD_COLOR)
	"""if ret:
		cv2.imshow('Frame', frame)
		c = cv2.waitKey(10)
	else:
		return False"""
	
	#update fps display
	counter += 1
	if counter >= 10:
		counter = 0
		fps = 10 / (time.time() - fpsTime)
		print("Current fps being read in is {} frames/seconds over last 10 frame. \r".format(fps))
		fpsTime = time.time()
	
	if ret == True:
		return frame
	else:
		return False

def sendAction(actionName, ip="192.168.1.2", port="8081"): #use this to send the wearable/pi a message describing the action we just saw
	resp = requests.post("http://{}:{}".format(ip, port), str(actionName))
	print(resp)
	return 1

def getPose(net, img, stride, upsample_ratio):
		num_keypoints = Pose.num_kpts
		previous_poses = []
		orig_img = img.copy()
		heatmaps, pafs, scale, pad = infer_fast(net, img, 256, stride, upsample_ratio, False)

		total_keypoints_num = 0
		all_keypoints_by_type = []
		for kpt_idx in range(num_keypoints):  # 19th for bg
			total_keypoints_num += extract_keypoints(heatmaps[:, :, kpt_idx], all_keypoints_by_type, total_keypoints_num)

		pose_entries, all_keypoints = group_keypoints(all_keypoints_by_type, pafs, demo=True)
		for kpt_id in range(all_keypoints.shape[0]):
			all_keypoints[kpt_id, 0] = (all_keypoints[kpt_id, 0] * stride / upsample_ratio - pad[1]) / scale
			all_keypoints[kpt_id, 1] = (all_keypoints[kpt_id, 1] * stride / upsample_ratio - pad[0]) / scale
		current_poses = []
		for n in range(len(pose_entries)):
			if len(pose_entries[n]) == 0:
				continue
			pose_keypoints = np.ones((num_keypoints, 2), dtype=np.int32) * -1
			for kpt_id in range(num_keypoints):
				if pose_entries[n][kpt_id] != -1.0:  # keypoint was found
					pose_keypoints[kpt_id, 0] = int(all_keypoints[int(pose_entries[n][kpt_id]), 0])
					pose_keypoints[kpt_id, 1] = int(all_keypoints[int(pose_entries[n][kpt_id]), 1])
			pose = Pose(pose_keypoints, pose_entries[n][18])
			current_poses.append(pose)
			pose.draw(img)

		img = cv2.addWeighted(orig_img, 0.6, img, 0.4, 0)
		"""if track_ids == True:
			propagate_ids(previous_poses, current_poses)
			previous_poses = current_poses
			for pose in current_poses:
				cv2.rectangle(img, (pose.bbox[0], pose.bbox[1]),
							  (pose.bbox[0] + pose.bbox[2], pose.bbox[1] + pose.bbox[3]), (0, 255, 0))
				cv2.putText(img, 'id: {}'.format(pose.id), (pose.bbox[0], pose.bbox[1] - 16),
							cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 0, 255))"""
		cv2.imshow('Lightweight Human Pose Estimation Python Demo', img)
		key = cv2.waitKey(33)
		if key == 27:  # esc
			return

if __name__ == "__main__":
	net = PoseEstimationWithMobileNet()
	net = net.cuda()
	checkpoint = torch.load("../lightweight-human-pose-estimation.pytorch/checkpoint_iter_370000.pth", map_location='cpu')
	load_state(net, checkpoint)

	cap = setupCam()

	timeCurr = time.time()
	frames = 0
	while True:
		frames += 1
		cvframe = getFrame(cap)
		getPose(net, cvframe, 8, 4)
		timeCurr = time.time()

	killCam(cap)

