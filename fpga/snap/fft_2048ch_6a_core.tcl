set repos [get_property ip_repo_paths [current_project]]
set_property ip_repo_paths "$repos /home/domagalski/wrk/spoco6/fft_2048ch_6a_core/ip" [current_project]
update_ip_catalog
create_ip -name fft_2048ch_6a_core -vendor User_Company -library SysGen -version 1.0 -module_name fft_2048ch_6a_core_ip
