import cv2
import numpy as np
import os
import pyperclip
import sys
import subprocess

def resize_and_crop_to_9_16(input_video_path, temp_video_path):
    """
    영상을 9:16 비율로 변환하고 두 개의 레이어 효과를 적용하는 함수 (오디오 제외)
    """
    cap = cv2.VideoCapture(input_video_path)
    
    if not cap.isOpened():
        error_msg = "영상을 열 수 없습니다."
        print(error_msg)
        pyperclip.copy(error_msg)
        return False
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    target_ratio = 9 / 16
    target_width = 1080
    target_height = int(target_width / target_ratio)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (target_width, target_height))
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        try:
            processed_frame = process_frame_for_9_16(frame, target_width, target_height)
            out.write(processed_frame)
        except Exception as e:
            error_msg = f"프레임 처리 중 오류 발생: {str(e)}"
            print(error_msg)
            pyperclip.copy(error_msg)
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            return False
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"처리된 프레임: {frame_count}/{total_frames}")
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    return True

def process_frame_for_9_16(frame, target_width, target_height):
    """
    단일 프레임을 9:16 비율로 처리하는 함수
    """
    h, w = frame.shape[:2]
    
    # 1단계: 첫 번째 레이어 (위아래 딱 맞게 확대 후 블러, 밝기 조정)
    scale_y = target_height / h
    scaled_width_1 = int(w * scale_y)
    layer1 = cv2.resize(frame, (scaled_width_1, target_height), interpolation=cv2.INTER_LINEAR)
    
    start_x_1 = (scaled_width_1 - target_width) // 2
    layer1_cropped = layer1[:, start_x_1:start_x_1 + target_width]
    
    # 블러 효과 적용
    layer1_blurred = cv2.GaussianBlur(layer1_cropped, (21, 21), 0)
    
    # 2단계: 두 번째 레이어 (양옆 35% 잘리게 확대, 위아래 여백 추가)
    scale_factor = 1.35
    new_width = int(target_width * scale_factor)
    # 타겟 높이의 60%로 조정하여 더 작게 설정
    adjusted_height = int(target_height * 0.6)
    scale_y_2 = adjusted_height / h
    scaled_width_2 = int(w * scale_y_2)
    layer2 = cv2.resize(frame, (scaled_width_2, adjusted_height), interpolation=cv2.INTER_LINEAR)
    
    # 중앙 정렬 및 여백 추가 (검은 박스 대신 layer1_blurred를 베이스로 사용하여 투명도 100 적용)
    top_margin = (target_height - adjusted_height) // 2
    bottom_margin = target_height - adjusted_height - top_margin
    layer2_with_margin = layer1_blurred.copy()  # 검은 박스를 투명하게 하기 위해 layer1_blurred 복사본 사용
    start_x_2 = (scaled_width_2 - target_width) // 2
    layer2_cropped = layer2[:, start_x_2:start_x_2 + target_width]
    
    # layer2_cropped를 불투명하게 (투명도 0) 오버레이
    layer2_with_margin[top_margin:top_margin + adjusted_height, :] = layer2_cropped
    
    # 최종 결과 (블렌딩 대신 직접 오버레이 사용)
    result = layer2_with_margin
    
    return result

def add_audio_to_video(input_video_path, temp_video_path, output_video_path, temp_audio_path='temp_audio.aac'):
    """
    입력 비디오에서 오디오를 추출하고 처리된 비디오에 추가하는 함수
    """
    # 오디오 추출
    extract_cmd = ['ffmpeg', '-i', input_video_path, '-vn', '-c:a', 'copy', temp_audio_path]
    try:
        result = subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("FFmpeg extract stderr:", result.stderr)
    except subprocess.CalledProcessError as e:
        error_msg = f"오디오 추출 중 오류 발생: {str(e)}\nStderr: {e.stderr}"
        print(error_msg)
        pyperclip.copy(error_msg)
        return False
    
    # 비디오와 오디오 병합 (재인코딩으로 호환성 확보)
    merge_cmd = ['ffmpeg', '-i', temp_video_path, '-i', temp_audio_path, '-c:v', 'libx264', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', output_video_path]
    try:
        result = subprocess.run(merge_cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("FFmpeg merge stderr:", result.stderr)
    except subprocess.CalledProcessError as e:
        error_msg = f"비디오와 오디오 병합 중 오류 발생: {str(e)}\nStderr: {e.stderr}"
        print(error_msg)
        pyperclip.copy(error_msg)
        return False
    
    # 임시 파일 삭제
    try:
        os.remove(temp_video_path)
        os.remove(temp_audio_path)
    except OSError as e:
        print(f"임시 파일 삭제 중 오류: {str(e)}")
    
    return True

def main():
    """
    메인 실행 함수
    """
    input_path = "input_video.mp4"
    temp_video_path = "temp_video.mp4"
    output_path = "output_9_16_short.mp4"
    temp_audio_path = "temp_audio.aac"
    
    if not os.path.exists(input_path):
        error_msg = f"입력 파일이 존재하지 않습니다: {input_path}"
        print(error_msg)
        print("input_video.mp4 파일을 준비해주세요.")
        pyperclip.copy(error_msg)
        return
    
    print("9:16 비율 영상 변환 프로그램을 시작합니다...")
    try:
        if resize_and_crop_to_9_16(input_path, temp_video_path):
            if add_audio_to_video(input_path, temp_video_path, output_path, temp_audio_path):
                print(f"영상 처리가 완료되었습니다. 출력: {output_path}")
            else:
                print("오디오 추가에 실패했습니다.")
        else:
            print("비디오 처리에 실패했습니다.")
    except Exception as e:
        error_msg = f"프로그램 실행 중 오류 발생: {str(e)}"
        print(error_msg)
        pyperclip.copy(error_msg)

if __name__ == "__main__":
    main()
