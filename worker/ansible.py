# iperf_runner.py
import os
import subprocess

def run_ansible_and_iperf(ip, user, password):
    """
    ฟังก์ชันหลัก: รัน Ansible (ติดตั้ง) และ iperf3 client (ทดสอบ)
    """
    print(f"▶️ [Worker] เริ่มทำงานกับ {ip}...")
    
    # --- ขั้นตอน A: รัน Ansible Playbook ---
    playbook_path = "ansible/playbook.yaml"
    config_path = "ansible/ansible.cfg"

    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = config_path

    ansible_cmd = [
        "ansible-playbook",
        "-i", f"{ip},",
        playbook_path,
        "--extra-vars", f"ansible_user={user} ansible_ssh_pass={password} ansible_become_pass={password}"
    ]
    
    print(f"  [Ansible] ติดตั้ง/เริ่ม iperf3 server บน {ip}...")
    process_ansible = subprocess.run(ansible_cmd, env=env, capture_output=True, text=True)  
    
    if process_ansible.returncode != 0:
        print(f"❌ [Ansible] ล้มเหลวสำหรับ {ip}:\n{process_ansible.stdout}\n{process_ansible.stderr}")
        raise Exception(f"Ansible failed: {process_ansible.stderr}")

    print(f"  [Ansible] ติดตั้งบน {ip} สำเร็จ")

    # --- ขั้นตอน B: รัน iPerf3 Client ---
    iperf_cmd = ["iperf3", "-c", ip, "-J"] # <-- นี่คือ TCP -J = JSON Output
    # ⬇️ เปลี่ยนเป็นแบบนี้เพื่อทดสอบ UDP ⬇️
    # (-u = UDP, -b 10M = ทดสอบที่ 10 Mbps)
    # iperf_cmd = ["iperf3", "-c", ip, "-J", "-u", "-b", "10M"]
    
    print(f"  [iperf3] เริ่มทดสอบกับ {ip}...")
    process_iperf = subprocess.run(iperf_cmd, capture_output=True, text=True)

    if process_iperf.returncode != 0:
        print(f"❌ [iperf3] ล้มเหลวสำหรับ {ip}:\n{process_iperf.stderr}")
        raise Exception(f"iperf3 failed: {process_iperf.stderr}")

    print(f"  [iperf3] ทดสอบ {ip} สำเร็จ")
    
    # คืนค่าผลลัพธ์ (stdout) ซึ่งเป็น JSON String
    return process_iperf.stdout