from string import letters, digits
from random import choice

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
import json

from instance.models import Instance
from servers.models import Compute

from vrtManager.instance import wvmInstances, wvmInstance

from libvirt import libvirtError, VIR_DOMAIN_XML_SECURE
from webvirtmgr.settings import TIME_JS_REFRESH


def instusage(request, host_id, vname):
    """
    Return instance usage
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    cookies = {}
    datasets = {}
    datasets_rd = []
    datasets_wr = []
    json_blk = []
    cookie_blk = {}
    blk_error = False
    datasets_rx = []
    datasets_tx = []
    json_net = []
    cookie_net = {}
    net_error = False

    compute = Compute.objects.get(id=host_id)

    try:
        conn = wvmInstance(compute.hostname,
                           compute.login,
                           compute.password,
                           compute.type,
                           vname)
        status = conn.get_status()
        if status == 5:
            networks = conn.get_net_device()
            disks = conn.get_disk_device()
    except libvirtError:
        status = None

    if status == 1 and status:
        try:
            blk_usage = conn.disk_usage()
            cpu_usage = conn.cpu_usage()
            net_usage = conn.net_usage()
            conn.close()
        except libvirtError:
            blk_usage = None
            cpu_usage = None
            net_usage = None

        try:
            cookies['cpu'] = request._cookies['cpu']
        except KeyError:
            cookies['cpu'] = None

        try:
            cookies['hdd'] = request._cookies['hdd']
        except KeyError:
            cookies['hdd'] = None

        try:
            cookies['net'] = request._cookies['net']
        except KeyError:
            cookies['net'] = None

        if cookies['cpu'] == '{}' or not cookies['cpu'] or not cpu_usage:
            datasets['cpu'] = [0]
        else:
            datasets['cpu'] = eval(cookies['cpu'])
        if len(datasets['cpu']) > 10:
            while datasets['cpu']:
                del datasets['cpu'][0]
                if len(datasets['cpu']) == 10:
                    break
        if len(datasets['cpu']) <= 9:
            datasets['cpu'].append(int(cpu_usage['cpu']))
        if len(datasets['cpu']) == 10:
            datasets['cpu'].append(int(cpu_usage['cpu']))
            del datasets['cpu'][0]

        # Some fix division by 0 Chart.js
        if len(datasets['cpu']) == 10:
            if sum(datasets['cpu']) == 0:
                datasets['cpu'][9] += 0.1
            if sum(datasets['cpu']) / 10 == datasets['cpu'][0]:
                datasets['cpu'][9] += 0.1

        cpu = {
            'labels': [""] * 10,
            'datasets': [
                {
                    "fillColor": "rgba(241,72,70,0.5)",
                    "strokeColor": "rgba(241,72,70,1)",
                    "pointColor": "rgba(241,72,70,1)",
                    "pointStrokeColor": "#fff",
                    "data": datasets['cpu']
                }
            ]
        }

        for blk in blk_usage:
            if cookies['hdd'] == '{}' or not cookies['hdd'] or not blk_usage:
                datasets_wr.append(0)
                datasets_rd.append(0)
            else:
                datasets['hdd'] = eval(cookies['hdd'])
                try:
                    datasets_rd = datasets['hdd'][blk['dev']][0]
                    datasets_wr = datasets['hdd'][blk['dev']][1]
                except:
                    blk_error = True

            if not blk_error:
                if len(datasets_rd) > 10:
                    while datasets_rd:
                        del datasets_rd[0]
                        if len(datasets_rd) == 10:
                            break
                if len(datasets_wr) > 10:
                    while datasets_wr:
                        del datasets_wr[0]
                        if len(datasets_wr) == 10:
                            break

                if len(datasets_rd) <= 9:
                    datasets_rd.append(int(blk['rd']) / 1048576)
                if len(datasets_rd) == 10:
                    datasets_rd.append(int(blk['rd']) / 1048576)
                    del datasets_rd[0]

                if len(datasets_wr) <= 9:
                    datasets_wr.append(int(blk['wr']) / 1048576)
                if len(datasets_wr) == 10:
                    datasets_wr.append(int(blk['wr']) / 1048576)
                    del datasets_wr[0]

                # Some fix division by 0 Chart.js
                if len(datasets_rd) == 10:
                    if sum(datasets_rd) == 0:
                        datasets_rd[9] += 0.01
                    if sum(datasets_rd) / 10 == datasets_rd[0]:
                        datasets_rd[9] += 0.01

                disk = {
                    'labels': [""] * 10,
                    'datasets': [
                        {
                            "fillColor": "rgba(83,191,189,0.5)",
                            "strokeColor": "rgba(83,191,189,1)",
                            "pointColor": "rgba(83,191,189,1)",
                            "pointStrokeColor": "#fff",
                            "data": datasets_rd
                        },
                        {
                            "fillColor": "rgba(249,134,33,0.5)",
                            "strokeColor": "rgba(249,134,33,1)",
                            "pointColor": "rgba(249,134,33,1)",
                            "pointStrokeColor": "#fff",
                            "data": datasets_wr
                        },
                    ]
                }

            json_blk.append({'dev': blk['dev'], 'data': disk})
            cookie_blk[blk['dev']] = [datasets_rd, datasets_wr]

        for net in net_usage:
            if cookies['net'] == '{}' or not cookies['net'] or not net_usage:
                datasets_rx.append(0)
                datasets_tx.append(0)
            else:
                datasets['net'] = eval(cookies['net'])
                try:
                    datasets_rx = datasets['net'][net['dev']][0]
                    datasets_tx = datasets['net'][net['dev']][1]
                except:
                    net_error = True

            if not net_error:
                if len(datasets_rx) > 10:
                    while datasets_rx:
                        del datasets_rx[0]
                        if len(datasets_rx) == 10:
                            break
                if len(datasets_tx) > 10:
                    while datasets_tx:
                        del datasets_tx[0]
                        if len(datasets_tx) == 10:
                            break

                if len(datasets_rx) <= 9:
                    datasets_rx.append(int(net['rx']) / 1048576)
                if len(datasets_rx) == 10:
                    datasets_rx.append(int(net['rx']) / 1048576)
                    del datasets_rx[0]

                if len(datasets_tx) <= 9:
                    datasets_tx.append(int(net['tx']) / 1048576)
                if len(datasets_tx) == 10:
                    datasets_tx.append(int(net['tx']) / 1048576)
                    del datasets_tx[0]

                # Some fix division by 0 Chart.js
                if len(datasets_rx) == 10:
                    if sum(datasets_rx) == 0:
                        datasets_rx[9] += 0.01
                    if sum(datasets_rx) / 10 == datasets_rx[0]:
                        datasets_rx[9] += 0.01

                network = {
                    'labels': [""] * 10,
                    'datasets': [
                        {
                            "fillColor": "rgba(83,191,189,0.5)",
                            "strokeColor": "rgba(83,191,189,1)",
                            "pointColor": "rgba(83,191,189,1)",
                            "pointStrokeColor": "#fff",
                            "data": datasets_rx
                        },
                        {
                            "fillColor": "rgba(151,187,205,0.5)",
                            "strokeColor": "rgba(151,187,205,1)",
                            "pointColor": "rgba(151,187,205,1)",
                            "pointStrokeColor": "#fff",
                            "data": datasets_tx
                        },
                    ]
                }

            json_net.append({'dev': net['dev'], 'data': network})
            cookie_net[net['dev']] = [datasets_rx, datasets_tx]

        data = json.dumps({'status': status, 'cpu': cpu, 'hdd': json_blk, 'net': json_net})
    else:
        datasets = [0] * 10
        cpu = {
            'labels': [""] * 10,
            'datasets': [
                {
                    "fillColor": "rgba(241,72,70,0.5)",
                    "strokeColor": "rgba(241,72,70,1)",
                    "pointColor": "rgba(241,72,70,1)",
                    "pointStrokeColor": "#fff",
                    "data": datasets
                }
            ]
        }

        for i, net in enumerate(networks):
            datasets_rx = [0] * 10
            datasets_tx = [0] * 10
            network = {
                'labels': [""] * 10,
                'datasets': [
                    {
                        "fillColor": "rgba(83,191,189,0.5)",
                        "strokeColor": "rgba(83,191,189,1)",
                        "pointColor": "rgba(83,191,189,1)",
                        "pointStrokeColor": "#fff",
                        "data": datasets_rx
                    },
                    {
                        "fillColor": "rgba(151,187,205,0.5)",
                        "strokeColor": "rgba(151,187,205,1)",
                        "pointColor": "rgba(151,187,205,1)",
                        "pointStrokeColor": "#fff",
                        "data": datasets_tx
                    },
                ]
            }
            json_net.append({'dev': i, 'data': network})

        for blk in disks:
            datasets_wr = [0] * 10
            datasets_rd = [0] * 10
            disk = {
                'labels': [""] * 10,
                'datasets': [
                    {
                        "fillColor": "rgba(83,191,189,0.5)",
                        "strokeColor": "rgba(83,191,189,1)",
                        "pointColor": "rgba(83,191,189,1)",
                        "pointStrokeColor": "#fff",
                        "data": datasets_rd
                    },
                    {
                        "fillColor": "rgba(249,134,33,0.5)",
                        "strokeColor": "rgba(249,134,33,1)",
                        "pointColor": "rgba(249,134,33,1)",
                        "pointStrokeColor": "#fff",
                        "data": datasets_wr
                    },
                ]
            }
            json_blk.append({'dev': blk['dev'], 'data': disk})
        data = json.dumps({'status': status, 'cpu': cpu, 'hdd': json_blk, 'net': json_net})

    response = HttpResponse()
    response['Content-Type'] = "text/javascript"
    if status == 1:
        response.cookies['cpu'] = datasets['cpu']
        response.cookies['hdd'] = cookie_blk
        response.cookies['net'] = cookie_net
    response.write(data)
    return response


def insts_status(request, host_id):
    """
    Instances block
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    errors = []
    instances = []
    compute = Compute.objects.get(id=host_id)

    try:
        conn = wvmInstances(compute.hostname,
                            compute.login,
                            compute.password,
                            compute.type)
        get_instances = conn.get_instances()
    except libvirtError as msg_error:
        errors.append(msg_error.message)

    for instance in get_instances:
        instances.append({'name': instance,
                          'status': conn.get_instance_status(instance),
                          'memory': conn.get_instance_memory(instance),
                          'vcpu': conn.get_instance_vcpu(instance),
                          'uuid': conn.get_uuid(instance),
                          'dump': conn.get_instance_managed_save_image(instance)
                          })

    data = json.dumps(instances)
    response = HttpResponse()
    response['Content-Type'] = "text/javascript"
    response.write(data)
    return response


def instances(request, host_id):
    """
    Instances block
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    errors = []
    instances = []
    time_refresh = 8000
    compute = Compute.objects.get(id=host_id)

    try:
        conn = wvmInstances(compute.hostname,
                            compute.login,
                            compute.password,
                            compute.type)
        get_instances = conn.get_instances()
    except libvirtError as msg_error:
        errors.append(msg_error.message)

    for instance in get_instances:
        try:
            inst = Instance.objects.get(compute_id=host_id, name=instance)
            uuid = inst.uuid
        except Instance.DoesNotExist:
            uuid = conn.get_uuid(instance)
            inst = Instance(compute_id=host_id, name=instance, uuid=uuid)
            inst.save()
        instances.append({'name': instance,
                          'status': conn.get_instance_status(instance),
                          'uuid': uuid,
                          'memory': conn.get_instance_memory(instance),
                          'vcpu': conn.get_instance_vcpu(instance),
                          'has_managed_save_image': conn.get_instance_managed_save_image(instance)})

    try:
        if request.method == 'POST':
            name = request.POST.get('name', '')
            if 'start' in request.POST:
                conn.start(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'shutdown' in request.POST:
                conn.shutdown(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'destroy' in request.POST:
                conn.force_shutdown(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'managedsave' in request.POST:
                conn.managedsave(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'deletesaveimage' in request.POST:
                conn.managed_save_remove(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'suspend' in request.POST:
                conn.suspend(name)
                return HttpResponseRedirect(request.get_full_path())
            if 'resume' in request.POST:
                conn.resume(name)
                return HttpResponseRedirect(request.get_full_path())

        conn.close()
    except libvirtError as msg_error:
        errors.append(msg_error.message)

    return render_to_response('instances.html', locals(), context_instance=RequestContext(request))


def instance(request, host_id, vname):
    """
    Instance block
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/login')

    errors = []
    messages = []
    time_refresh = TIME_JS_REFRESH
    compute = Compute.objects.get(id=host_id)
    computes = Compute.objects.all()
    computes_count = len(computes)

    try:
        conn = wvmInstance(compute.hostname,
                           compute.login,
                           compute.password,
                           compute.type,
                           vname)

        status = conn.get_status()
        autostart = conn.get_autostart()
        vcpu = conn.get_vcpu()
        cur_vcpu = conn.get_cur_vcpu()
        uuid = conn.get_uuid()
        memory = conn.get_memory()
        cur_memory = conn.get_cur_memory()
        description = conn.get_description()
        disks = conn.get_disk_device()
        media = conn.get_media_device()
        networks = conn.get_net_device()
        media_iso = sorted(conn.get_iso_media())
        vcpu_range = conn.get_max_cpus()
        memory_range = [256, 512, 1024, 2048, 4096, 6144, 8192, 16384]
        memory_host = conn.get_max_memory()
        vcpu_host = len(vcpu_range)
        vnc_port = conn.get_vnc()
        snapshots = sorted(conn.get_snapshot(), reverse=True)
        inst_xml = conn._XMLDesc(VIR_DOMAIN_XML_SECURE)
        has_managed_save_image = conn.get_managed_save_image()
    except libvirtError as msg_error:
        errors.append(msg_error.message)

    try:
        instance = Instance.objects.get(compute_id=host_id, name=vname)
        if instance.uuid != uuid:
            instance.uuid = uuid
            instance.save()
    except Instance.DoesNotExist:
        instance = Instance(compute_id=host_id, name=vname, uuid=uuid)
        instance.save()

    try:
        if request.method == 'POST':
            if 'start' in request.POST:
                conn.start()

                return HttpResponseRedirect(request.get_full_path())
            if 'power' in request.POST:
                if 'shutdown' == request.POST.get('power', ''):
                    conn.shutdown()
                    return HttpResponseRedirect(request.get_full_path())
                if 'destroy' == request.POST.get('power', ''):
                    conn.force_shutdown()
                    return HttpResponseRedirect(request.get_full_path())
                if 'managedsave' == request.POST.get('power', ''):
                    conn.managedsave()
                    return HttpResponseRedirect(request.get_full_path())
            if 'deletesaveimage' in request.POST:
                conn.managed_save_remove()
                return HttpResponseRedirect(request.get_full_path())
            if 'suspend' in request.POST:
                conn.suspend()
                return HttpResponseRedirect(request.get_full_path())
            if 'resume' in request.POST:
                conn.resume()
                return HttpResponseRedirect(request.get_full_path())
            if 'delete' in request.POST:
                if conn.get_status() == 1:
                    conn.force_shutdown()
                if request.POST.get('delete_disk', ''):
                    conn.delete_disk()
                try:
                    instance = Instance.objects.get(compute_id=host_id, name=vname)
                    instance.delete()
                finally:
                    conn.delete()
                return HttpResponseRedirect('/instances/%s/' % host_id)
            if 'snapshot' in request.POST:
                name = request.POST.get('name', '')
                conn.create_snapshot(name)
                msg = _("Snapshot '%s' has been created successful" % name)
                messages.append(msg)
            if 'umount_iso' in request.POST:
                image = request.POST.get('iso_media', '')
                conn.umount_iso(image)
                return HttpResponseRedirect(request.get_full_path())
            if 'mount_iso' in request.POST:
                image = request.POST.get('iso_media', '')
                conn.mount_iso(image)
                return HttpResponseRedirect(request.get_full_path())
            if 'set_autostart' in request.POST:
                conn.set_autostart(1)
                return HttpResponseRedirect(request.get_full_path())
            if 'unset_autostart' in request.POST:
                conn.set_autostart(0)
                return HttpResponseRedirect(request.get_full_path())
            if 'change_settings' in request.POST:
                description = request.POST.get('description', '')
                vcpu = request.POST.get('vcpu', '')
                cur_vcpu = request.POST.get('cur_vcpu', '')
                memory = request.POST.get('memory', '')
                cur_memory = request.POST.get('cur_memory', '')
                conn.change_settings(description, cur_memory, memory, cur_vcpu, vcpu)
                return HttpResponseRedirect(request.get_full_path())
            if 'change_xml' in request.POST:
                xml = request.POST.get('inst_xml', '')
                if xml:
                    conn._defineXML(xml)
                    return HttpResponseRedirect(request.get_full_path())
            if 'set_vnc_passwd' in request.POST:
                if request.POST.get('auto_pass', ''):
                    passwd = ''.join([choice(letters + digits) for i in xrange(12)])
                else:
                    passwd = request.POST.get('vnc_passwd', '')
                    if not passwd:
                        msg = _("Enter the VNC password or select Generate")
                        errors.append(msg)
                if not errors:
                    conn.set_vnc_passwd(passwd)
                    return HttpResponseRedirect(request.get_full_path())
            if 'migrate' in request.POST:
                compute_id = request.POST.get('compute_id', '')
                new_compute = Compute.objects.get(id=compute_id)
                conn_migrate = wvmInstances(new_compute.hostname,
                                            new_compute.login,
                                            new_compute.password,
                                            new_compute.type)
                conn_migrate.moveto(conn, vname)
                conn_migrate.define_move(vname)
                conn_migrate.close()
                return HttpResponseRedirect('/instance/%s/%s' % (compute_id, vname))
            if 'delete_snapshot' in request.POST:
                snap_name = request.POST.get('name', '')
                conn.snapshot_delete(snap_name)
                return HttpResponseRedirect(request.get_full_path())
            if 'revert_snapshot' in request.POST:
                snap_name = request.POST.get('name', '')
                conn.snapshot_revert(snap_name)
                msg = _("Successful revert snapshot: ")
                msg += snap_name
                messages.append(msg)

        conn.close()

    except libvirtError as msg_error:
        errors.append(msg_error.message)

    return render_to_response('instance.html', locals(), context_instance=RequestContext(request))
