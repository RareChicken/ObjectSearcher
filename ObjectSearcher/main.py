#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import os
import shutil
from timeit import time
import warnings
import sys
import cv2
import numpy as np
from PIL import Image
# from yolo import YOLO
from darknet_yolo import YOLO
from darknet_yolo import array_to_image

from deep_sort import preprocessing
from deep_sort import nn_matching
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker
from tools import generate_detections as gdet
from deep_sort.detection import Detection as ddet
warnings.filterwarnings('ignore')

def main(yolo):

   # Definition of the parameters
    max_cosine_distance = 0.3
    nn_budget = None
    nms_max_overlap = 1.0
    
   # deep_sort 
    model_filename = 'model_data/mars-small128.pb'
    encoder = gdet.create_box_encoder(model_filename,batch_size=1)
    
    metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
    tracker = Tracker(metric)

    writeVideo_flag = False
    
    video_capture = cv2.VideoCapture('data/test.mp4')

    if writeVideo_flag:
    # Define the codec and create VideoWriter object
        w = int(video_capture.get(3))
        h = int(video_capture.get(4))
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter('output.avi', fourcc, 15, (w, h))
        list_file = open('detection.txt', 'w')
        frame_index = -1

    if os.path.exists('detections'):
        shutil.rmtree('detections')
    # 이 파일을 참조하고 있는 경우 Permission 에러 발생
    os.mkdir('detections')
        
    last_id = 0;
    fps = 0.0
    while True:
        ret, original_frame = video_capture.read()
        ret, frame = video_capture.read()  # frame shape 640*480*3
        if ret != True:
            break;
        t1 = time.time()

        # image = Image.fromarray(frame)
        image, arr = array_to_image(frame)
        dets = yolo.detect_image(image)

        # print("box_num",len(boxs))
        boxes = [det[1] for det in dets]
        features = encoder(frame, boxes)
        
        # score to 1.0 here).
        detections = [Detection(det[0], det[1], 1.0, feature) for det, feature in zip(dets, features)]
        
        # Run non-maxima suppression.
        boxes = np.array([d.tlwh for d in detections])
        scores = np.array([d.confidence for d in detections])
        indices = preprocessing.non_max_suppression(boxes, nms_max_overlap, scores)
        detections = [detections[i] for i in indices]
        
        # Call the tracker
        tracker.predict()
        tracker.update(detections)

        for track in tracker.tracks:
            if track.is_confirmed() and track.time_since_update >1 :
                continue
            bbox = track.to_tlbr()
            x = int(bbox[0])
            y = int(bbox[1])
            w = int(bbox[2])
            h = int(bbox[3])
            cv2.rectangle(frame, (x, y), (w, h), (255,255,255), 2)
            cv2.putText(frame, str(track.track_id), (x, y), 0, 5e-3 * 200, (0,255,0), 2)
            # 새롭게 아이디가 부여된 객체 사진 일단 저장
            if track.track_id > last_id:
                image_trim = original_frame[y:h, x:w]
                cv2.imwrite(os.path.join('detections', track.clazz + '_' + str(track.track_id) + '.jpg'), image_trim)

        last_id = tracker._next_id - 1;

        for det in detections:
            bbox = det.to_tlbr()
            x = int(bbox[0])
            y = int(bbox[1])
            w = int(bbox[2])
            h = int(bbox[3])
            cv2.rectangle(frame, (x, y), (w, h), (255,0,0), 2)
            cv2.putText(frame, det.clazz, (x, y), 0, 5e-3 * 200, (0,0,255), 2)
            
        cv2.imshow('', frame)
        
        if writeVideo_flag:
            # save a frame
            out.write(frame)
            frame_index = frame_index + 1
            list_file.write(str(frame_index)+' ')
            if len(boxes) != 0:
                for i in range(0,len(boxes)):
                    list_file.write(str(boxes[i][0]) + ' '+str(boxes[i][1]) + ' '+str(boxes[i][2]) + ' '+str(boxes[i][3]) + ' ')
            list_file.write('\n')
            
        fps  = ( fps + (1./(time.time()-t1)) ) / 2
        print("fps= %f"%(fps))
        
        # Press Q to stop!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    if writeVideo_flag:
        out.release()
        list_file.close()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main(YOLO())
