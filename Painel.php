<?
$CMD_TERMINATE_PROCESS = 1;
$CMD_ACTIVATE_PROCESS = 2;
$CMD_CREATE_REPORT = 3;
$CMD_SYNC_NOW = 4;
$CMD_SEE_REPORT = 5;
$RB_NOHUP_CMD = 'nohup';
$RB_PYTHON_CMD = '/opt/bin/python';
$RB_NO_OUTPUT_CMD = '>/dev/null 2>&1 &';
$RB_DIR = '/shares/fabriciokury/Arquivo/Trabalhos/RB/';
$RB_SCRIPT_FILE = $RB_DIR.'rb.py';
$RB_FILE_PROCESS_ID = $RB_DIR.'rbpid.dat';
$RB_FILE_REPORT_LINK = 'relatorio.html';
$process_is_running = false;
$pid = 0;
$exec_output = 0;

$text_style = 'font-size:20pt;';
$button_style = 'font-size:30pt;'; 

function update_process_status() {    
    global $RB_FILE_PROCESS_ID, $pid, $process_is_running;
    $pid = file($RB_FILE_PROCESS_ID);
    $pid = intval($pid[0]);
    if(file_exists('/proc/'.$pid)) {
        $process_is_running = true;
    }
    else
        $process_is_running = false;
}

if(isset($_POST["$CMD_SEE_REPORT"]))
   header('Location: '.$RB_FILE_REPORT_LINK);

update_process_status();

if(isset($_POST["$CMD_TERMINATE_PROCESS"]))
{
    global $exec_output;
    $exec_output =  shell_exec('kill '.$pid);
    update_process_status();
}

if(isset($_POST["$CMD_ACTIVATE_PROCESS"]))
{
    shell_exec("$RB_NOHUP_CMD $RB_PYTHON_CMD $RB_SCRIPT_FILE $RB_NO_OUTPUT_CMD");
    sleep(2);
    update_process_status();
    $i = 0;
    global $process_is_running;
    while($i<10){ // Number of seconds to wait
        if(!$process_is_running) {
            sleep(1);
            update_process_status();
        }
        $i++;
    }
}

if(isset($_POST["$CMD_CREATE_REPORT"]))
{
    echo shell_exec("$RB_PYTHON_CMD $RB_SCRIPT_FILE -r $RB_NO_OUTPUT_CMD");
    echo '<span style="'.$text_style.'"><i>O relatorio foi solicitado.</i></span>';
}

if(isset($_POST["$CMD_SYNC_NOW"]))
{
    echo exec("$RB_PYTHON_CMD $RB_SCRIPT_FILE -u $RB_NO_OUTPUT_CMD");
    echo '<span style="'.$text_style.'"><i>A sincronizacao foi solicitada.</i></span>';
} ?>
<html>
<head>
<title>Renova Backup - Painel de Controle</title>
</head>
<body>
<h1><span style="color: #AA0000;">Renova Backup v0.5</span></h1>
<h2>Por Fabricio Kury -- fabriciokury arroba gmail (.) com -- Celular: +1-301-281-5414</h2>
<form action="<?=$_SERVER['PHP_SELF']?>" method="post">
<p><span style="<?=$text_style?> color: #<?=$process_is_running?'00CC22':'CC0000'?>;"> O processo esta: <?=$process_is_running?"Ativo (ID = $pid)":'Inativo'?></span></p>
<?/*<p><input style="font-size:20pt;" type="submit" name="<?=$process_is_running?$CMD_TERMINATE_PROCESS:$CMD_ACTIVATE_PROCESS?>" value="<?=$process_is_running?'Terminar processo':'Ativar processo'?>"></p>*/?>
<p><input style="<?=$button_style?>" type="submit" name="<?=$CMD_SEE_REPORT?>" value="Ver relatorio"></p>
<? if($process_is_running) {
    ?><p><input style="<?=$button_style?>" type="submit" name="<?=$CMD_CREATE_REPORT?>" value="Gerar relatorio agora"></p>
<br>
<br>
<p><input style="<?=$button_style?>" type="submit" name="<?=$CMD_SYNC_NOW?>" value="Sincronizar agora"></p><?
} ?>
</form>
<? {
    global $exec_output;
    if($exec_output)
        echo '<p>'.nl2br($exec_output).'</p>';
} ?>

</body>
</html>
