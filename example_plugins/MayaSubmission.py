from __future__ import absolute_import
import traceback
import re
import imp  # For Integration UI
import os
from typing import Any, Text

from System import *
from System.Collections.Specialized import StringCollection
from System.IO import Path, StreamWriter, File, Directory
from System.Text import Encoding

from Deadline.Scripting import RepositoryUtils, FrameUtils, ClientUtils, PathUtils, StringUtils

from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog

from ThinkboxUI.Controls.Scripting.ComboControl import ComboControl
from ThinkboxUI.Controls.Scripting.CheckBoxControl import CheckBoxControl
from ThinkboxUI.Controls.Scripting.ButtonControl import ButtonControl
from ThinkboxUI.Controls.Scripting.IScriptControl import IScriptControl
imp.load_source( 'IntegrationUI', RepositoryUtils.GetRepositoryFilePath( "submission/Integration/Main/IntegrationUI.py", True ) )
import IntegrationUI

########################################################################
## Globals
########################################################################
scriptDialog = None  # type: DeadlineScriptDialog
integration_dialog = None
outputBox = None  # type: IScriptControl
sceneBox = None  # type: IScriptControl
defaultLocation = None
settings = None
ProjectManagementOptions = ["Shotgun","FTrack","NIM"]
DraftRequested = False
supported_versions = ("2010", "2011", "2011.5", "2012", "2012.5", "2013", "2013.5", "2014", "2014.5",
                      "2015", "2015.5", "2016", "2016.5", "2017", "2017.5", "2018", "2019", "2020", 
                      "2022", "2023", "2024")

########################################################################
## Main Function Called By Deadline
########################################################################
def __main__( *args ):
    # type: (*Any) -> None
    global scriptDialog
    global settings
    global defaultLocation
    global outputBox
    global sceneBox
    global ProjectManagementOptions
    global DraftRequested
    global integration_dialog

    defaultLocation = ""
    
    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle( "Submit Maya Job To Deadline" )
    scriptDialog.SetIcon( scriptDialog.GetIcon( 'MayaBatch' ) )
    
    scriptDialog.AddTabControl("Tabs", 0, 0)
    
    scriptDialog.AddTabPage("Job Options")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator1", "SeparatorControl", "Job Description", 0, 0, colSpan=2 )
    
    scriptDialog.AddControlToGrid( "NameLabel", "LabelControl", "Job Name", 1, 0, "The name of your job. This is optional, and if left blank, it will default to 'Untitled'.", False )
    scriptDialog.AddControlToGrid( "NameBox", "TextControl", "Untitled", 1, 1 )

    scriptDialog.AddControlToGrid( "CommentLabel", "LabelControl", "Comment", 2, 0, "A simple description of your job. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "CommentBox", "TextControl", "", 2, 1 )

    scriptDialog.AddControlToGrid( "DepartmentLabel", "LabelControl", "Department", 3, 0, "The department you belong to. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "DepartmentBox", "TextControl", "", 3, 1 )

    scriptDialog.AddControlToGrid( "PingLabel", "LabelControl", "Ping user(s)", 4, 0, "Discord user to ping / claim job.", False )
    scriptDialog.AddControlToGrid( "PingBox", "TextControl", "", 4, 1 )

    scriptDialog.EndGrid()

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator2", "SeparatorControl", "Job Options", 0, 0, colSpan=3 )

    scriptDialog.AddControlToGrid( "PoolLabel", "LabelControl", "Pool", 1, 0, "The pool that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "PoolBox", "PoolComboControl", "none", 1, 1 )

    scriptDialog.AddControlToGrid( "SecondaryPoolLabel", "LabelControl", "Secondary Pool", 2, 0, "The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Workers.", False )
    scriptDialog.AddControlToGrid( "SecondaryPoolBox", "SecondaryPoolComboControl", "", 2, 1 )

    scriptDialog.AddControlToGrid( "GroupLabel", "LabelControl", "Group", 3, 0, "The group that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "GroupBox", "GroupComboControl", "none", 3, 1 )

    scriptDialog.AddControlToGrid( "PriorityLabel", "LabelControl", "Priority", 4, 0, "A job can have a numeric priority ranging from 0 to 100, where 0 is the lowest priority and 100 is the highest priority.", False )
    scriptDialog.AddRangeControlToGrid( "PriorityBox", "RangeControl", RepositoryUtils.GetMaximumPriority() // 2, 0, RepositoryUtils.GetMaximumPriority(), 0, 1, 4, 1 )

    scriptDialog.AddControlToGrid( "TaskTimeoutLabel", "LabelControl", "Task Timeout", 5, 0, "The number of minutes a Worker has to render a task for this job before it requeues it. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "TaskTimeoutBox", "RangeControl", 0, 0, 1000000, 0, 1, 5, 1 )
    scriptDialog.AddSelectionControlToGrid( "AutoTimeoutBox", "CheckBoxControl", False, "Enable Auto Task Timeout", 5, 2, "If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job." )

    scriptDialog.AddControlToGrid( "ConcurrentTasksLabel", "LabelControl", "Concurrent Tasks", 6, 0, "The number of tasks that can render concurrently on a single Worker. This is useful if the rendering application only uses one thread to render and your Workers have multiple CPUs.", False )
    scriptDialog.AddRangeControlToGrid( "ConcurrentTasksBox", "RangeControl", 1, 1, 16, 0, 1, 6, 1 )
    scriptDialog.AddSelectionControlToGrid( "LimitConcurrentTasksBox", "CheckBoxControl", True, "Limit Tasks To Worker's Task Limit", 6, 2, "If you limit the tasks to a Worker's task limit, then by default, the Worker won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual Workers by an administrator." )

    scriptDialog.AddControlToGrid( "MachineLimitLabel", "LabelControl", "Machine Limit", 7, 0, "", False )
    scriptDialog.AddRangeControlToGrid( "MachineLimitBox", "RangeControl", 0, 0, 1000000, 0, 1, 7, 1 )
    scriptDialog.AddSelectionControlToGrid( "IsBlacklistBox", "CheckBoxControl", False, "Machine List Is A Deny List", 7, 2, "" )

    scriptDialog.AddControlToGrid( "MachineListLabel", "LabelControl", "Machine List", 8, 0, "Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.", False )
    scriptDialog.AddControlToGrid( "MachineListBox", "MachineListControl", "", 8, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "LimitGroupLabel", "LabelControl", "Limits", 9, 0, "The Limits that your job requires.", False )
    scriptDialog.AddControlToGrid( "LimitGroupBox", "LimitGroupControl", "", 9, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "DependencyLabel", "LabelControl", "Dependencies", 10, 0, "Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering.", False )
    scriptDialog.AddControlToGrid( "DependencyBox", "DependencyControl", "", 10, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "OnJobCompleteLabel", "LabelControl", "On Job Complete", 11, 0, "If desired, you can automatically archive or delete the job when it completes.", False )
    scriptDialog.AddControlToGrid( "OnJobCompleteBox", "OnJobCompleteControl", "Nothing", 11, 1 )
    scriptDialog.AddSelectionControlToGrid( "SubmitSuspendedBox", "CheckBoxControl", False, "Submit Job As Suspended", 11, 2, "If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render." )
    scriptDialog.EndGrid()

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator3", "SeparatorControl", "Maya Options", 0, 0, colSpan=4 )

    scriptDialog.AddControlToGrid("ProjectLabel","LabelControl","Project Directory", 1, 0, "The Maya project folder (this should be a shared folder on the network).", False)
    projBox = scriptDialog.AddSelectionControlToGrid("ProjectBox","FolderBrowserControl","","", 1, 1, colSpan=3)
    projBox.ValueModified.connect(SetDefaultLocation)
    defaultLocation = scriptDialog.GetValue( "ProjectBox" )

    scriptDialog.AddControlToGrid( "SceneLabel", "LabelControl", "Maya File", 2, 0, "The scene file to be rendered.", False )
    sceneBox = scriptDialog.AddSelectionControlToGrid( "SceneBox", "MultiFileBrowserControl", "", "Maya Files (*.ma *.mb)", 2, 1, colSpan=3, browserLocation=defaultLocation )

    scriptDialog.AddControlToGrid("OutputLabel","LabelControl","Output Folder",3, 0, "The folder where your output will be dumped (this should be a shared folder on the network).", False)
    outputBox = scriptDialog.AddSelectionControlToGrid("OutputBox","FolderBrowserControl", "","", 3, 1, colSpan=3, browserLocation=defaultLocation)

    scriptDialog.AddControlToGrid( "FramesLabel", "LabelControl", "Frame List", 4, 0, "The list of frames to render.", False )
    scriptDialog.AddControlToGrid( "FramesBox", "TextControl", "", 4, 1 )
    scriptDialog.AddSelectionControlToGrid( "SubmitSceneBox", "CheckBoxControl", False, "Submit Maya Scene File", 4, 2, "If this option is enabled, the scene file will be submitted with the job, and then copied locally to the Worker machine during rendering.", colSpan=2 )

    scriptDialog.AddControlToGrid( "ChunkSizeLabel", "LabelControl", "Frames Per Task", 5, 0, "This is the number of frames that will be rendered at a time for each job task.", False )
    scriptDialog.AddRangeControlToGrid( "ChunkSizeBox", "RangeControl", 1, 1, 1000000, 0, 1, 5, 1 )
    scriptDialog.AddControlToGrid( "RendererLabel", "LabelControl", "Renderer", 5, 2, "The Maya renderer to use. If you select 'File', the renderer defined in the scene file will be used, but renderer specific options will not be set by Deadline.", False )
    rendererBox = scriptDialog.AddComboControlToGrid( "RendererBox", "ComboControl", "File", ("File","3delight","Arnold","FinalRender","Gelato","Maxwell","MayaKrakatoa","MayaHardware","MayaHardware2","MayaSoftware","MayaVector","MentalRay","OctaneRender","Redshift","Renderman","RendermanRIS","Renderman22","Turtle","Vray","Iray"), 5, 3 )
    rendererBox.ValueModified.connect( RendererChanged )

    scriptDialog.AddControlToGrid( "VersionLabel", "LabelControl", "Version", 6, 0, "The version of Maya to render with.", False )
    versionBox = scriptDialog.AddComboControlToGrid( "VersionBox", "ComboControl", supported_versions[-1], supported_versions, 6, 1 )
    versionBox.ValueModified.connect( VersionChanged )
    scriptDialog.AddControlToGrid( "BuildLabel", "LabelControl", "Build To Force", 6, 2, "You can force 32 or 64 bit rendering with this option.", False )
    scriptDialog.AddComboControlToGrid( "BuildBox", "ComboControl", "None", ( "None", "32bit", "64bit" ), 6, 3 )

    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    
    scriptDialog.AddTabPage( "Advanced Options" )

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator5", "SeparatorControl", "Advanced Maya Options", 0, 0, colSpan=3 )

    scriptDialog.AddControlToGrid( "CpusLabel", "LabelControl", "Threads", 1, 0, "The number of threads to use for rendering.", False )
    scriptDialog.AddRangeControlToGrid( "CpusBox", "RangeControl", 0, 0, 256, 0, 1, 1, 1 )
    scriptDialog.AddSelectionControlToGrid( "LocalRenderingBox", "CheckBoxControl", False, "Enable Local Rendering", 1, 2, "If enabled, the frames will be rendered locally, and then copied to their final network location." )

    scriptDialog.AddControlToGrid( "FrameNumberOffsetLabel", "LabelControl", "Frame Number Offset", 2, 0, "Uses Maya's frame renumbering option to offset the frames that are rendered.", False )
    scriptDialog.AddRangeControlToGrid( "FrameNumberOffsetBox", "RangeControl", 0, -100000, 100000, 0, 1, 2, 1 )
    scriptDialog.AddSelectionControlToGrid( "StrictErrorCheckingBox", "CheckBoxControl", True, "Strict Error Checking", 2, 2, "Enable this option to have Deadline fail Maya jobs when Maya prints out any 'error' or 'warning' messages. If disabled, Deadline will only fail on messages that it knows are fatal." )

    mayaBatchBox = scriptDialog.AddSelectionControlToGrid( "MayaBatchBox", "CheckBoxControl", True, "Use MayaBatch Plugin", 3, 0, "This uses the MayaBatch plugin. It keeps the scene loaded in memory between frames, which reduces the overhead of rendering the job.", False )
    mayaBatchBox.ValueModified.connect(MayaBatchChanged)
    scriptDialog.AddSelectionControlToGrid( "Ignore211Box", "CheckBoxControl", False, "Ignore Error Code 211", 3, 1, "This allows a MayaCmd task to finish successfully even if Maya returns the non-zero error code 211. Sometimes Maya will return this error code even after successfully saving the rendered images.", False )
    scriptDialog.AddSelectionControlToGrid( "SkipExistingBox", "CheckBoxControl", False, "Skip Existing Frames", 3, 2, "If enabled, Maya will skip rendering existing frames. Only supported for Maya Softwate, Maya Hardware, Maya Vector, and Mentay Ray." )

    scriptDialog.AddControlToGrid( "StartupScriptLabel", "LabelControl", "Startup Script", 4, 0, "Maya will source the specified script file on startup.", False )
    scriptDialog.AddSelectionControlToGrid( "StartupScriptBox", "FileBrowserControl", "", "Melscript Files (*.mel);;Python Files (*.py);;All Files (*)", 4, 1, colSpan=2 )
    
    overrideSizeBox = scriptDialog.AddSelectionControlToGrid( "OverrideSizeBox", "CheckBoxControl", False, "Override Resolution", 5, 0, "Enable this option to override the Width and Height (respectively) of the rendered images.", colSpan=1)
    scriptDialog.AddRangeControlToGrid( "WidthSizeRange", "RangeControl", 0, 0, 1000000, 0, 1, 5, 1)
    scriptDialog.AddRangeControlToGrid( "HeightSizeRange", "RangeControl", 0, 0, 1000000, 0, 1, 5, 2)
    overrideSizeBox.ValueModified.connect(OverrideSizeChanged)
    OverrideSizeChanged()
    
    scaleBox = scriptDialog.AddSelectionControlToGrid( "ScaleBox", "CheckBoxControl", False, "Scale Resolution", 6, 0, "Enable this option to scale the size of the rendered images to the specified percentage.", colSpan=1)
    scriptDialog.AddRangeControlToGrid( "ScaleRange", "RangeControl", 100, 0.01, 1000, 2, 1, 6, 1)
    scaleBox.ValueModified.connect(ScaleChanged)
    ScaleChanged()

    scriptDialog.AddSelectionControlToGrid( "FileUsesLegacyRenderLayersBox", "CheckBoxControl", False, "File Uses Legacy Render Layers", 6, 2, "As of Maya 2016.5, Autodesk has added a new render layer system (render setup) that is incompatible with the older version (legacy). This value specifies which render layers system this file uses." )
    
    scriptDialog.AddSelectionControlToGrid( "RenderSetupIncludeLightsBox", "CheckBoxControl", True, "Include all lights in each Render Layer", 7, 0, "If enabled, all lights in the scene will automatically be added to every render setup.", colSpan=2 )
    
    scriptDialog.EndGrid()
    
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator4", "SeparatorControl", "Command Line Options", 0, 0, colSpan=2 )

    scriptDialog.AddControlToGrid( "CommandLineLabel", "LabelControl", "Additional Arguments", 1, 0, "Specify additional command line arguments you would like to pass to the renderer.", False )
    scriptDialog.AddControlToGrid( "CommandLineBox", "TextControl", "", 1, 1 )

    scriptDialog.AddSelectionControlToGrid( "UseCommandLineBox", "CheckBoxControl", False, "Use Only Additional Command Line Arguments", 2, 0, "Enable this option to only use the command line arguments specified above when rendering.", colSpan=2 )

    scriptDialog.AddControlToGrid( "Separator7", "SeparatorControl", "Script Job Options", 3, 0, colSpan=2 )
    scriptDialog.AddControlToGrid( "ScriptJobLabel1", "LabelControl", "Script Jobs use the MayaBatch plugin, and do not force a particular render.", 4, 0, colSpan=2 )
    scriptJobBox = scriptDialog.AddSelectionControlToGrid( "ScriptJobBox", "CheckBoxControl", False, "Submit A Maya Script Job (melscript or python)", 5, 0, "Enable this option to submit a custom melscript or python script job. This script will be applied to the scene file that is specified.", colSpan=2 )
    scriptJobBox.ValueModified.connect(ScriptJobChanged)

    scriptDialog.AddControlToGrid( "ScriptFileLabel", "LabelControl", "Script File", 6, 0, "The script file to use.", False )
    scriptDialog.AddSelectionControlToGrid( "ScriptFileBox", "FileBrowserControl", "", "Maya Script Files (*.mel *.py)", 6, 1 )

    scriptDialog.AddControlToGrid( "ScriptJobLabel2", "LabelControl", "All other options on this tab page are ignored, except for the Strict Error Checking option.", 7, 0, colSpan=2 )
    
    scriptDialog.EndGrid()
    
    scriptDialog.EndTabPage()
    
    scriptDialog.AddTabPage( "Renderer Options" )
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "ArnoldSeparator", "SeparatorControl", "Arnold Options", 0, 0, colSpan=3 )

    scriptDialog.AddControlToGrid( "MayaToArnoldVersionLabel", "LabelControl", "Maya To Arnold Major Version", 1, 0, "Specify the version number of the Maya To Arnold plugin that will be used.", False )
    scriptDialog.AddComboControlToGrid( "MayaToArnoldVersionBox", "ComboControl", "2", ("1","2","3"), 1, 1 )

    scriptDialog.AddControlToGrid( "ArnoldVerboseLabel", "LabelControl", "Arnold Verbosity", 2, 0, "Set the verbosity level for Arnold renders. Note that verbosity levels are different depending on the Maya To Arnold version.", False )
    scriptDialog.AddComboControlToGrid( "ArnoldVerboseBox", "ComboControl", "1", ("0","1","2", "3"), 2, 1 )
    scriptDialog.AddHorizontalSpacerToGrid("ROHSpacer1", 2, 2)

    scriptDialog.AddControlToGrid( "MentalRaySeparator", "SeparatorControl", "Mental Ray Options", 3, 0, colSpan=3 )

    scriptDialog.AddControlToGrid( "MentalRayVerboseLabel", "LabelControl", "Mental Ray Verbosity", 4, 0, "Set the verbosity level for Mental Ray renders.", False )
    scriptDialog.AddComboControlToGrid( "MentalRayVerboseBox", "ComboControl", "Progress Messages", ("No Messages","Fatal Messages Only","Error Messages","Warning Messages","Info Messages","Progress Messages","Detailed Messages (Debug)"), 4, 1 )

    autoMemoryLimitBox = scriptDialog.AddSelectionControlToGrid( "AutoMemoryLimitBox", "CheckBoxControl", True, "Auto Memory Limit", 5, 0, "If enabled, Mental Ray will automatically detect the optimal memory limit when rendering.", False )
    autoMemoryLimitBox.ValueModified.connect(AutoMemoryLimitChanged)

    scriptDialog.AddControlToGrid( "MemoryLimitLabel", "LabelControl", "Memory Limit (in MB)", 6, 0, "Soft limit (in MB) for the memory used by Mental Ray (specify 0 for unlimited memory).", False )
    scriptDialog.AddRangeControlToGrid( "MemoryLimitBox", "RangeControl", 0, 0, 100000, 0, 1, 6, 1 )

    scriptDialog.AddControlToGrid( "VRaySeparator", "SeparatorControl", "VRay Options", 7, 0, colSpan=3 )

    vrayAutoMemoryBox = scriptDialog.AddSelectionControlToGrid( "VRayAutoMemoryBox", "CheckBoxControl", False, "Auto Memory Limit Detection (Requires the MayaBatch Plugin)", 8, 0, "If enabled, Deadline will automatically detect the dynamic memory limit for VRay prior to rendering.", colSpan=2 )
    vrayAutoMemoryBox.ValueModified.connect(VRayAutoMemoryChanged)

    scriptDialog.AddControlToGrid( "VRayMemoryLimitLabel", "LabelControl", "Memory Buffer (in MB)", 9, 0, "Deadline subtracts this value from the system's unused memory to determine the dynamic memory limit for VRay.", False )
    scriptDialog.AddRangeControlToGrid( "VRayMemoryLimitBox", "RangeControl", 500, 0, 100000, 0, 1, 9, 1 )
    
    scriptDialog.AddControlToGrid( "IRaySeparator", "SeparatorControl", "IRay Options", 10, 0, colSpan=3 )
    
    irayUseCPUsBox = scriptDialog.AddSelectionControlToGrid( "IRayUseCPUsBox", "CheckBoxControl", True, "Render Using CPUs", 11, 0, "If enabled, CPUs will be used to render the scene in addition to GPUs." )
    irayUseCPUsBox.ValueModified.connect(IRayUseCPUsChanged)
    scriptDialog.AddControlToGrid( "IRayCPULoadLabel", "LabelControl", "CPU Load", 11, 1, "The maximum load on the CPU for each task.", False )
    scriptDialog.AddRangeControlToGrid( "IRayCPULoadBox", "RangeControl", 1.0, 4.0, 8, 1, 0.1, 11, 2 )
    
    scriptDialog.AddControlToGrid( "IRayMaxSamplesLabel", "LabelControl", "Max Samples", 12, 0, "The Maximum number of samples per frame.", False )
    scriptDialog.AddRangeControlToGrid( "IRayMaxSamplesBox", "RangeControl", 1, 1, 4096, 0, 1, 12, 1 )
    
    scriptDialog.AddControlToGrid( "GPUSeparator", "SeparatorControl", "GPU Options", 13, 0, colSpan=3 )
    
    scriptDialog.AddControlToGrid( "GPUsPerTaskLabel", "LabelControl", "GPUs Per Task", 14, 0, "The number of GPUs to use per task. If set to 0, the default number of GPUs will be used, unless 'Select GPU Devices' Id's have been defined.", False )
    GPUsPerTaskBox = scriptDialog.AddRangeControlToGrid( "GPUsPerTaskBox", "RangeControl", 0, 0, 16, 0, 1, 14, 1 )
    GPUsPerTaskBox.ValueModified.connect(GPUsPerTaskChanged)

    scriptDialog.AddControlToGrid( "GPUsSelectDevicesLabel", "LabelControl", "Select GPU Devices", 15, 0, "A comma separated list of the GPU devices to use specified by device Id. 'GPUs Per Task' will be ignored.", False )
    GPUsSelectDevicesBox = scriptDialog.AddControlToGrid( "GPUsSelectDevicesBox", "TextControl", "", 15, 1 )
    GPUsSelectDevicesBox.ValueModified.connect(GPUsSelectDevicesChanged)
    
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    
    integration_dialog = IntegrationUI.IntegrationDialog()
    integration_dialog.AddIntegrationTabs( scriptDialog, "MayaMonitor", DraftRequested, ProjectManagementOptions, failOnNoTabs=False )
    
    scriptDialog.EndTabControl()
    
    scriptDialog.AddGrid()
    scriptDialog.AddHorizontalSpacerToGrid( "HSpacer1", 0, 0 )
    submitButton = scriptDialog.AddControlToGrid( "SubmitButton", "ButtonControl", "Submit", 0, 1, expand=False )
    submitButton.ValueModified.connect(SubmitButtonPressed)
    closeButton = scriptDialog.AddControlToGrid( "CloseButton", "ButtonControl", "Close", 0, 2, expand=False )
    # Make sure all the project management connections are closed properly
    closeButton.ValueModified.connect(integration_dialog.CloseProjectManagementConnections)
    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    scriptDialog.EndGrid()

    settings = ( "DepartmentBox","CategoryBox","PoolBox","SecondaryPoolBox","GroupBox","PriorityBox","MachineLimitBox","IsBlacklistBox","MachineListBox","LimitGroupBox","SceneBox","FramesBox","ChunkSizeBox","VersionBox","BuildBox","ProjectBox", "OutputBox", "RendererBox", "SubmitSceneBox", "MayaBatchBox","LocalRenderingBox","CpusBox","StrictErrorCheckingBox","StartupScriptBox","OverrideSizeBox","WidthSizeRange","HeightSizeRange","FileUsesLegacyRenderLayersBox","CommandLineBox","UseCommandLineBox","RenderSetupIncludeLightsBox","PingBox")
    scriptDialog.LoadSettings( GetSettingsFilename(), settings )
    scriptDialog.EnabledStickySaving( settings, GetSettingsFilename() )
    
    GPUsPerTaskChanged()
    GPUsSelectDevicesChanged()
    IRayUseCPUsChanged()
    VersionChanged()
    RendererChanged()
    MayaBatchChanged()
    AutoMemoryLimitChanged()
    VRayAutoMemoryChanged()
    ScriptJobChanged()
    
    scriptDialog.ShowDialog( False )
    
def SetDefaultLocation():
    # type: () -> None
    global defaultLocation
    global scriptDialog
    global sceneBox
    global outputBox
    
    defaultLocation = scriptDialog.GetValue( "ProjectBox" )
    
    sceneLocation = os.path.join(defaultLocation, "scenes")  # type: ignore
    outputLocation = os.path.join(defaultLocation, "images")  # type: ignore
    
    if not os.path.exists(sceneLocation):
        sceneLocation = defaultLocation  # type: ignore
    if not os.path.exists(outputLocation):
        outputLocation = defaultLocation  # type: ignore
    
    outputBox.setBrowserLocation( outputLocation )
    sceneBox.setBrowserLocation( sceneLocation )
      
def GetSettingsFilename():
    # type: () -> str
    return Path.Combine( ClientUtils.GetUsersSettingsDirectory(), "MayaSettings.ini" )

def VersionChanged(*args):
    # type: (*ComboControl) -> None
    global scriptDialog
    maya_version = float(scriptDialog.GetValue("VersionBox"))

    renderer = scriptDialog.GetValue("RendererBox")
    skipExistingEnabled = maya_version >= 2014 and renderer in ("MayaHardware", "MayaHardware2", "MayaVector", "MayaSoftware", "MentalRay")
    scriptDialog.SetEnabled("SkipExistingBox", skipExistingEnabled)

    legacyRenderLayersEnabled = maya_version >= 2016.5
    scriptDialog.SetEnabled("FileUsesLegacyRenderLayersBox", legacyRenderLayersEnabled)

    includeLightsEnabled = maya_version >= 2018
    scriptDialog.SetEnabled("RenderSetupIncludeLightsBox", includeLightsEnabled)

def RendererChanged(*args):
    # type: (*ComboControl) -> None
    global scriptDialog

    enabled = ( scriptDialog.GetValue( "RendererBox" ) != "3delight" )
    scriptDialog.SetEnabled( "OutputLabel", enabled )
    scriptDialog.SetEnabled( "OutputBox", enabled )

    renderer = scriptDialog.GetValue("RendererBox" )
    threadsEnabled = (renderer in { "MayaSoftware", "MentalRay", "Renderman", "RendermanRIS", "Renderman22", "3delight", "FinalRender", "Maxwell", "Vray" } )
    scriptDialog.SetEnabled( "CpusLabel", threadsEnabled )
    scriptDialog.SetEnabled( "CpusBox", threadsEnabled )

    localEnabled = not ( renderer == "Renderman22"  )
    scriptDialog.SetEnabled( "LocalRenderingBox", localEnabled )

    fileEnabled = not (renderer == "File")
    scriptDialog.SetEnabled( "FrameNumberOffsetLabel", fileEnabled )
    scriptDialog.SetEnabled( "FrameNumberOffsetBox", fileEnabled )
    scriptDialog.SetEnabled( "OverrideSizeBox", fileEnabled )

    arEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "Arnold" )
    scriptDialog.SetEnabled( "ArnoldSeparator", arEnabled )
    scriptDialog.SetEnabled( "MayaToArnoldVersionLabel", arEnabled )
    scriptDialog.SetEnabled( "MayaToArnoldVersionBox", arEnabled )
    scriptDialog.SetEnabled( "ArnoldVerboseLabel", arEnabled )
    scriptDialog.SetEnabled( "ArnoldVerboseBox", arEnabled )

    mrEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "MentalRay" )
    scriptDialog.SetEnabled( "MentalRaySeparator", mrEnabled )
    scriptDialog.SetEnabled( "MentalRayVerboseLabel", mrEnabled )
    scriptDialog.SetEnabled( "MentalRayVerboseBox", mrEnabled )
    scriptDialog.SetEnabled( "AutoMemoryLimitBox", mrEnabled )

    mlEnabled = not scriptDialog.GetValue( "AutoMemoryLimitBox" )
    scriptDialog.SetEnabled( "MemoryLimitLabel", mrEnabled and mlEnabled )
    scriptDialog.SetEnabled( "MemoryLimitBox", mrEnabled and mlEnabled )

    vrayEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "Vray" )
    batchEnabled = scriptDialog.GetValue( "MayaBatchBox" )
    memEnabled = scriptDialog.GetValue( "VRayAutoMemoryBox" )
    scriptDialog.SetEnabled( "VRaySeparator", vrayEnabled )
    scriptDialog.SetEnabled( "VRayAutoMemoryBox", vrayEnabled and batchEnabled )
    scriptDialog.SetEnabled( "VRayMemoryLimitLabel", vrayEnabled and memEnabled and batchEnabled )
    scriptDialog.SetEnabled( "VRayMemoryLimitBox", vrayEnabled and memEnabled and batchEnabled )
    
    irayEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "Iray" )
    scriptDialog.SetEnabled( "IRaySeparator", irayEnabled )
    scriptDialog.SetEnabled( "IRayUseCPUsBox", irayEnabled )
    scriptDialog.SetEnabled( "IRayCPULoadLabel", irayEnabled )
    scriptDialog.SetEnabled( "IRayCPULoadBox", irayEnabled )
    scriptDialog.SetEnabled( "IRayMaxSamplesLabel", irayEnabled )
    scriptDialog.SetEnabled( "IRayMaxSamplesBox", irayEnabled )
    
    gpuEnabled = ( ( scriptDialog.GetValue( "RendererBox" ) == "Iray" ) or ( scriptDialog.GetValue( "RendererBox" ) == "Redshift" ) or ( scriptDialog.GetValue( "RendererBox" ) == "OctaneRender" ) or ( scriptDialog.GetValue( "RendererBox" ) == "Vray" ) )
    scriptDialog.SetEnabled( "GPUSeparator", gpuEnabled )
    scriptDialog.SetEnabled( "GPUsPerTaskLabel", gpuEnabled )
    scriptDialog.SetEnabled( "GPUsPerTaskBox", gpuEnabled )
    scriptDialog.SetEnabled( "GPUsSelectDevicesLabel", gpuEnabled )
    scriptDialog.SetEnabled( "GPUsSelectDevicesBox", gpuEnabled )

    skipExistingEnabled = (float(scriptDialog.GetValue( "VersionBox" )) >= 2014) and (renderer == "MayaHardware" or renderer == "MayaHardware2" or renderer == "MayaVector" or renderer == "MayaSoftware" or renderer == "MentalRay")
    scriptDialog.SetEnabled( "SkipExistingBox", skipExistingEnabled )
    
def MayaBatchChanged(*args):
    global scriptDialog
    
    batchEnabled = scriptDialog.GetValue( "MayaBatchBox" )
    scriptDialog.SetEnabled( "Ignore211Box", not batchEnabled )
    scriptDialog.SetEnabled( "StartupScriptLabel", batchEnabled )
    scriptDialog.SetEnabled( "StartupScriptBox", batchEnabled )
    scriptDialog.SetEnabled( "Separator4", not batchEnabled )
    scriptDialog.SetEnabled( "CommandLineLabel", not batchEnabled )
    scriptDialog.SetEnabled( "CommandLineBox", not batchEnabled )
    scriptDialog.SetEnabled( "UseCommandLineBox", not batchEnabled )
    
    vrayEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "Vray" )
    memEnabled = scriptDialog.GetValue( "VRayAutoMemoryBox" )
    scriptDialog.SetEnabled( "VRayAutoMemoryBox", vrayEnabled and batchEnabled )
    scriptDialog.SetEnabled( "VRayMemoryLimitLabel", vrayEnabled and memEnabled and batchEnabled )
    scriptDialog.SetEnabled( "VRayMemoryLimitBox", vrayEnabled and memEnabled and batchEnabled )
    
def AutoMemoryLimitChanged(*args):
    global scriptDialog
    
    mlEnabled = not scriptDialog.GetValue( "AutoMemoryLimitBox" )
    mrEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "MentalRay" )
    
    scriptDialog.SetEnabled( "MemoryLimitLabel", mrEnabled and mlEnabled )
    scriptDialog.SetEnabled( "MemoryLimitBox", mrEnabled and mlEnabled )

def GPUsPerTaskChanged(*args):
    global scriptDialog

    perTaskEnabled = ( scriptDialog.GetValue( "GPUsPerTaskBox" ) == 0 )

    scriptDialog.SetEnabled( "GPUsSelectDevicesLabel", perTaskEnabled )
    scriptDialog.SetEnabled( "GPUsSelectDevicesBox", perTaskEnabled )

def GPUsSelectDevicesChanged(*args):
    # type: (*Any) -> None
    global scriptDialog

    selectDeviceEnabled = ( scriptDialog.GetValue( "GPUsSelectDevicesBox" ) == "" )

    scriptDialog.SetEnabled( "GPUsPerTaskLabel", selectDeviceEnabled )
    scriptDialog.SetEnabled( "GPUsPerTaskBox", selectDeviceEnabled )

def IRayUseCPUsChanged(*args):
    global scriptDialog
    
    scriptDialog.SetEnabled( "IRayCPULoadBox", scriptDialog.GetValue( "IRayUseCPUsBox" ) )
 
def OverrideSizeChanged(*args):
    # type: (*CheckBoxControl) -> None
    global scriptDialog
    overrideEnabled = scriptDialog.GetValue( "OverrideSizeBox" )
    
    scriptDialog.SetEnabled( "WidthSizeRange", overrideEnabled )
    scriptDialog.SetEnabled( "HeightSizeRange", overrideEnabled )

def ScaleChanged(*args):
    global scriptDialog
    scaleEnabled = scriptDialog.GetValue( "ScaleBox" )
    
    scriptDialog.SetEnabled( "ScaleRange", scaleEnabled )

def VRayAutoMemoryChanged(*args):
    # type: (*CheckBoxControl) -> None
    global scriptDialog
    
    vrayEnabled = ( scriptDialog.GetValue( "RendererBox" ) == "Vray" )
    batchEnabled = scriptDialog.GetValue( "MayaBatchBox" )
    memEnabled = scriptDialog.GetValue( "VRayAutoMemoryBox" )
    
    scriptDialog.SetEnabled( "VRayMemoryLimitLabel", vrayEnabled and memEnabled and batchEnabled )
    scriptDialog.SetEnabled( "VRayMemoryLimitBox", vrayEnabled and memEnabled and batchEnabled )

def ScriptJobChanged(*args):
    # type: (*CheckBoxControl) -> None
    global scriptDialog
    
    enabled = scriptDialog.GetValue( "ScriptJobBox" )
    scriptDialog.SetEnabled( "ScriptFileLabel", enabled )
    scriptDialog.SetEnabled( "ScriptFileBox", enabled )
    scriptDialog.SetEnabled( "ScriptJobLabel2", enabled )
    
def SubmitButtonPressed( *args ):
    # type: (*ButtonControl) -> None
    global scriptDialog
    global integration_dialog
    
    try:
        renderer = scriptDialog.GetValue( "RendererBox" )
        scriptJob = scriptDialog.GetValue( "ScriptJobBox" )
        
        if renderer == "Iray":
            renderer == "ifmIrayPhotoreal"
        
        # Check if maya files.
        sceneFiles = StringUtils.FromSemicolonSeparatedString( scriptDialog.GetValue( "SceneBox" ), False )
        if( len( sceneFiles ) == 0 ):
            scriptDialog.ShowMessageBox( "No Maya file specified", "Error" )
            return
        
        for sceneFile in sceneFiles:
            if( not File.Exists( sceneFile ) ):
                scriptDialog.ShowMessageBox( "Maya file %s does not exist" % sceneFile, "Error" )
                return
            #if the submit scene box is checked check if they are local, if they are warn the user
            elif( not bool( scriptDialog.GetValue("SubmitSceneBox") ) and PathUtils.IsPathLocal( sceneFile ) ):
                result = scriptDialog.ShowMessageBox( "The scene file " + sceneFile + " is local, are you sure you want to continue?", "Warning", ("Yes","No") )
                if( result == "No" ):
                    return
        
        # Check project folder.
        projectFolder = (scriptDialog.GetValue( "ProjectBox" )).strip()
        if( not Directory.Exists( projectFolder ) ):
            scriptDialog.ShowMessageBox( "Project folder %s does not exist" % projectFolder, "Error" )
            return
        elif( PathUtils.IsPathLocal( projectFolder ) ):
            result = scriptDialog.ShowMessageBox( "Project folder " + projectFolder + " is local, are you sure you want to continue?", "Warning", ("Yes","No") )
            if( result == "No" ):
                return
        
        # Check output folder.
        outputFolder = (scriptDialog.GetValue( "OutputBox" )).strip()
        if( not scriptJob and renderer != "3delight" ):
            if( not Directory.Exists( outputFolder ) ):
                scriptDialog.ShowMessageBox( "Output folder %s does not exist" % outputFolder, "Error" )
                return
            elif( PathUtils.IsPathLocal( outputFolder ) ):
                result = scriptDialog.ShowMessageBox( "Output folder " + outputFolder + " is local, are you sure you want to continue?", "Warning", ("Yes","No") )
                if( result == "No" ):
                    return
        
        # Check startup script
        startupScriptFile = scriptDialog.GetValue( "StartupScriptBox" ).strip()
        if scriptDialog.GetValue( "MayaBatchBox" ) and len(startupScriptFile) > 0:
            if( not File.Exists( startupScriptFile ) ):
                scriptDialog.ShowMessageBox( "Startup Script file %s does not exist" % startupScriptFile, "Error" )
                return
            elif ( PathUtils.IsPathLocal( startupScriptFile ) ):
                result = scriptDialog.ShowMessageBox( "Startup Script file %s is local, are you sure you want to continue?" % startupScriptFile, "Warning", ("Yes","No") )
                if( result == "No" ):
                    return
        
        # Check script
        scriptFile = (scriptDialog.GetValue( "ScriptFileBox" )).strip()
        if( scriptJob ):
            if( not File.Exists( scriptFile ) ):
                scriptDialog.ShowMessageBox( "Script file %s does not exist" % scriptFile, "Error" )
                return

        # Check if Integration options are valid
        if integration_dialog is not None and not integration_dialog.CheckIntegrationSanity():
            return

        # Check if a valid frame range has been specified.
        frames = scriptDialog.GetValue( "FramesBox" )
        if( not FrameUtils.FrameRangeValid( frames ) ):
            scriptDialog.ShowMessageBox( "Frame range %s is not valid" % frames, "Error" )
            return
            
        # If Redshift and using 'select GPU device Ids' then check device Id syntax is valid
        if( ( renderer == "Redshift" or renderer == "ifmIrayPhotoreal" or renderer == "OctaneRender" or renderer == "Vray") and scriptDialog.GetValue( "GPUsPerTaskBox" ) == 0 and scriptDialog.GetValue( "GPUsSelectDevicesBox" ) != "" ):
            regex = re.compile( "^(\d{1,2}(,\d{1,2})*)?$" )
            validSyntax = regex.match( scriptDialog.GetValue( "GPUsSelectDevicesBox" ) )
            if not validSyntax:
                scriptDialog.ShowMessageBox( "'Select GPU Devices' syntax is invalid!\n\nTrailing 'commas' if present, should be removed.\n\nValid Examples: 0 or 2 or 0,1,2 or 0,3,4 etc", "Error" )
                return

            # Check if concurrent threads > 1
            if scriptDialog.GetValue( "ConcurrentTasksBox" ) > 1:
                scriptDialog.ShowMessageBox( "If using 'Select GPU Devices', then 'Concurrent Tasks' must be set to 1", "Error" )
                return

        successes = 0
        failures = 0
        
        # Submit each scene file separately.
        for sceneFile in sceneFiles:
            # Create job info file.Fexecute
            jobInfoFilename = Path.Combine( ClientUtils.GetDeadlineTempPath(), "maya_job_info.job" )
            writer = StreamWriter( jobInfoFilename, False, Encoding.Unicode )
            if( scriptJob or scriptDialog.GetValue( "MayaBatchBox" ) ):
                writer.WriteLine( "Plugin=MayaBatch" )
            else:
                writer.WriteLine( "Plugin=MayaCmd" )
            
            jobName = scriptDialog.GetValue( "NameBox" )
            
            if len( sceneFiles ) > 1:
                jobName = jobName + " [" + Path.GetFileName( sceneFile ) + "]"
                
            if scriptJob:
                jobName = jobName + " [Script Job]"
            
            writer.WriteLine( "Name=%s" % jobName )
            writer.WriteLine( "Comment=%s" % scriptDialog.GetValue( "CommentBox" ) )
            writer.WriteLine( "Department=%s" % scriptDialog.GetValue( "DepartmentBox" ) )
            writer.WriteLine( "Pool=%s" % scriptDialog.GetValue( "PoolBox" ) )
            writer.WriteLine( "SecondaryPool=%s" % scriptDialog.GetValue( "SecondaryPoolBox" ) )
            writer.WriteLine( "Group=%s" % scriptDialog.GetValue( "GroupBox" ) )
            writer.WriteLine( "Priority=%s" % scriptDialog.GetValue( "PriorityBox" ) )
            writer.WriteLine( "TaskTimeoutMinutes=%s" % scriptDialog.GetValue( "TaskTimeoutBox" ) )
            writer.WriteLine( "EnableAutoTimeout=%s" % scriptDialog.GetValue( "AutoTimeoutBox" ) )
            writer.WriteLine( "ConcurrentTasks=%s" % scriptDialog.GetValue( "ConcurrentTasksBox" ) )
            writer.WriteLine( "LimitConcurrentTasksToNumberOfCpus=%s" % scriptDialog.GetValue( "LimitConcurrentTasksBox" ) )
            
            writer.WriteLine( "MachineLimit=%s" % scriptDialog.GetValue( "MachineLimitBox" ) )
            if( bool(scriptDialog.GetValue( "IsBlacklistBox" )) ):
                writer.WriteLine( "Blacklist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
            else:
                writer.WriteLine( "Whitelist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
            
            writer.WriteLine( "LimitGroups=%s" % scriptDialog.GetValue( "LimitGroupBox" ) )
            writer.WriteLine( "JobDependencies=%s" % scriptDialog.GetValue( "DependencyBox" ) )
            writer.WriteLine( "OnJobComplete=%s" % scriptDialog.GetValue( "OnJobCompleteBox" ) )
            
            if( bool(scriptDialog.GetValue( "SubmitSuspendedBox" )) ):
                writer.WriteLine( "InitialStatus=Suspended" )
            
            writer.WriteLine( "Frames=%s" % frames )
            writer.WriteLine( "ChunkSize=%s" % scriptDialog.GetValue( "ChunkSizeBox" ) )
            
            if( not scriptJob and renderer != "3delight" ):
                writer.WriteLine( "OutputDirectory0=%s" % outputFolder )
            
            # Integration
            extraKVPIndex = 0
            groupBatch = False
            
            if integration_dialog is not None and integration_dialog.IntegrationProcessingRequested():
                extraKVPIndex = integration_dialog.WriteIntegrationInfo( writer, extraKVPIndex )
                groupBatch = groupBatch or integration_dialog.IntegrationGroupBatchRequested()
                        
            if groupBatch:
                writer.WriteLine( "BatchName=%s\n" % ( jobName ) )

            ## Write ping data. ##
            pingname = str(scriptDialog.GetValue("PingBox")).replace("@","")
            writer.WriteLine("ExtraInfoKeyValue0=JobPing=%s" % pingname)

            writer.Close()
            
            # Create plugin info file.
            pluginInfoFilename = Path.Combine( ClientUtils.GetDeadlineTempPath(), "maya_plugin_info.job" )
            writer = StreamWriter( pluginInfoFilename, False, Encoding.Unicode )
            
            if( not bool(scriptDialog.GetValue( "SubmitSceneBox" )) ):
                writer.WriteLine( "SceneFile=%s" % sceneFile )
            
            writer.WriteLine( "Version=%s" % scriptDialog.GetValue( "VersionBox" ) )
            writer.WriteLine( "Build=%s" % scriptDialog.GetValue( "BuildBox" ) )
            writer.WriteLine( "ProjectPath=%s" % projectFolder )
            writer.WriteLine( "StrictErrorChecking=%s" % scriptDialog.GetValue( "StrictErrorCheckingBox" ) )
            writer.WriteLine( "UseLegacyRenderLayers=%s" % int( scriptDialog.GetValue( "FileUsesLegacyRenderLayersBox" ) ) )
            writer.WriteLine( "RenderSetupIncludeLights=%s" % int( scriptDialog.GetValue( "RenderSetupIncludeLightsBox" ) ) )
            
            if scriptJob:
                writer.WriteLine( "ScriptJob=True" )
                writer.WriteLine( "ScriptFilename=%s" % Path.GetFileName( scriptFile ) )
            else:
                writer.WriteLine( "LocalRendering=%s" % scriptDialog.GetValue( "LocalRenderingBox" ) )
                writer.WriteLine( "MaxProcessors=%s" % scriptDialog.GetValue( "CpusBox" ) )
                writer.WriteLine( "FrameNumberOffset=%s" % scriptDialog.GetValue( "FrameNumberOffsetBox" ) )
                
                if( renderer != "3delight" ):
                    writer.WriteLine( "OutputFilePath=%s" % outputFolder )
                
                writer.WriteLine( "Renderer=%s" % renderer )
                if( renderer == "Arnold" ):
                    # The max verbosity level is dependent on the MtoA version.
                    arnoldVersionMaxVerbosity = {
                        1 : 2,
                        2 : 2,
                        3 : 3
                    }
                    mtoaVersion = int(scriptDialog.GetValue("MayaToArnoldVersionBox"))
                    arnoldVerbosity = int(scriptDialog.GetValue("MayaToArnoldVersionBox"))
                    # Arnold will error if the verbosity level is higher than the maximum
                    if arnoldVerbosity > arnoldVersionMaxVerbosity[mtoaVersion]:
                        arnoldVerbosity = arnoldVersionMaxVerbosity[mtoaVersion]
                    writer.WriteLine("MayaToArnoldVersion=%d" % mtoaVersion)
                    writer.WriteLine("ArnoldVerbose=%d" % arnoldVerbosity)
                elif( renderer == "MentalRay" ):
                    writer.WriteLine( "MentalRayVerbose=%s" % scriptDialog.GetValue( "MentalRayVerboseBox" ) )
                    writer.WriteLine( "AutoMemoryLimit=%s" % scriptDialog.GetValue( "AutoMemoryLimitBox" ) )
                    writer.WriteLine( "MemoryLimit=%s" % scriptDialog.GetValue( "MemoryLimitBox" ) )
                elif( renderer == "Vray" and scriptDialog.GetValue( "MayaBatchBox" ) ):
                    writer.WriteLine( "VRayAutoMemoryEnabled=%s" % scriptDialog.GetValue( "VRayAutoMemoryBox" ) )
                    writer.WriteLine( "VRayAutoMemoryBuffer=%s" % scriptDialog.GetValue( "VRayMemoryLimitBox" ) )
                elif( renderer == "ifmIrayPhotoreal" ):
                    writer.WriteLine( "IRayUseCPUs=%s" % scriptDialog.GetValue( "IRayUseCPUsBox" ) )
                    writer.WriteLine( "IRayCPULoad=%s" % scriptDialog.GetValue( "IRayCPULoadBox" ) )
                    writer.WriteLine( "IRayMaxSamples=%s" % scriptDialog.GetValue( "IRayMaxSamplesBox" ) )
                
                if( renderer == "Redshift" or renderer == "ifmIrayPhotoreal" or renderer == "OctaneRender" or renderer == "Vray" ):
                    writer.WriteLine( "GPUsPerTask=%s" % scriptDialog.GetValue( "GPUsPerTaskBox" ) )
                    writer.WriteLine( "GPUsSelectDevices=%s" % scriptDialog.GetValue( "GPUsSelectDevicesBox" ) )
                
                if scriptDialog.GetValue( "MayaBatchBox" ):
                    writer.WriteLine( "StartupScript=%s" % startupScriptFile )
                
                writer.WriteLine( "CommandLineOptions=%s" % scriptDialog.GetValue( "CommandLineBox" ).strip() )
                writer.WriteLine( "UseOnlyCommandLineOptions=%d" % scriptDialog.GetValue( "UseCommandLineBox" ) )
                writer.WriteLine( "IgnoreError211=%s" % scriptDialog.GetValue( "Ignore211Box" ) )
                
                if (float(scriptDialog.GetValue( "VersionBox" )) >= 2014) and (renderer == "MayaHardware" or renderer == "MayaHardware2" or renderer == "MayaVector" or renderer == "MayaSoftware" or renderer == "MentalRay"):
                    writer.WriteLine( "SkipExistingFrames=%s" % scriptDialog.GetValue( "SkipExistingBox" ) )
                    
                if scriptDialog.GetValue( "OverrideSizeBox" ):
                    writer.WriteLine( "ImageWidth=%s" % scriptDialog.GetValue( "WidthSizeRange" ) )
                    writer.WriteLine( "ImageHeight=%s" % scriptDialog.GetValue( "HeightSizeRange" ) )
                
                if scriptDialog.GetValue( "ScaleBox" ):
                    writer.WriteLine( "ImageScale=%s" % scriptDialog.GetValue( "ScaleRange" ) )
                
            writer.Close()
            
            # Setup the command line arguments.
            arguments = StringCollection()
            
            arguments.Add( jobInfoFilename )
            arguments.Add( pluginInfoFilename )

            if scriptDialog.GetValue( "SubmitSceneBox" ):
                arguments.Add( sceneFile )

            if scriptJob:
                arguments.Add( scriptFile )
            
            if( len( sceneFiles ) == 1 ):
                results = ClientUtils.ExecuteCommandAndGetOutput( arguments )
                scriptDialog.ShowMessageBox( results, "Submission Results" )
            else:
                # Now submit the job.
                exitCode = ClientUtils.ExecuteCommand( arguments )
                if( exitCode == 0 ):
                    successes = successes + 1
                else:
                    failures = failures + 1
            
        if( len( sceneFiles ) > 1 ):
            scriptDialog.ShowMessageBox( "Jobs submitted successfully: %d\nJobs not submitted: %d" % (successes, failures), "Submission Results" )
    except:
        ClientUtils.LogText( str(traceback.format_exc()) )
