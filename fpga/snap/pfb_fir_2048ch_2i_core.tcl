set repos [get_property ip_repo_paths [current_project]]
set_property ip_repo_paths "$repos /home/domagalski/wrk/spoco6/pfb_fir_2048ch_2i_core/ip" [current_project]
update_ip_catalog
create_ip -name pfb_fir_2048ch_2i_core -vendor User_Company -library SysGen -version 1.0 -module_name pfb_fir_2048ch_2i_core_ip
