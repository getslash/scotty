# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.define :server do |server|
    server.vm.box = "debian/jessie64"
    server.vm.host_name = "server"
    server.vm.network "forwarded_port", guest: 80, host: 8080
    server.vm.network "private_network", ip: "192.168.50.3"
    server.vm.provision "ansible" do |ansible|
      ansible.groups = {
        "webapp" => ["server"],
        "db" => ["server"],
      }
      ansible.playbook = "ansible/site.yml"
      ansible.extra_vars = {
        install_with_debug: false,
        production: false,
        transporter_host: "192.168.50.3",
      }
      ansible.sudo = true
    end
  config.vm.define :host do |host|
    host.vm.box = "trusty64"
    host.vm.box_url = "http://cloud-images.ubuntu.com/vagrant/trusty/current/trusty-server-cloudimg-amd64-vagrant-disk1.box"
    host.vm.host_name = "host"
    host.vm.network "private_network", ip: "192.168.50.4"
  end
end
