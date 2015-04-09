# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.define :server do |server|
    server.vm.box = "trusty64"
    server.vm.box_url = "http://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
    server.vm.host_name = "server"
    server.vm.forward_port 80, 8000
    server.vm.provision "ansible" do |ansible|
      ansible.groups = {
        "webapp" => ["server"],
        "db" => ["server"],
      }
      ansible.playbook = "ansible/site.yml"
      ansible.extra_vars = {
        install_with_debug: true
      }
      ansible.sudo = true
    end
  end

  config.vm.define :host do |host|
    host.vm.box = "trusty64"
    host.vm.box_url = "http://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
    host.vm.host_name = "host"
    host.vm.network "private_network", ip: "192.168.50.4"
  end
end
