"""
Create CSV tables per section from settings file.

@author: Sascha Holzhauer
"""
import pandas as pd
import os
import pathlib


def create_doc(
        create_rst = False,
        inputfilename = "../../../../../src/settings/settings.toml",
        rstcsvtemplate = "settings_csv.tmpl",
    ):
    """
    Create CSV tables per section from settings file.
    Comment lines above a setting are parsed to column "Annotations".
    
    Parameters
    ----------
    create_rst: bool
        if True the RST file linking to CSV tables is created anew
    inputfilename: str
        the filename including path to the default settings toml file
    rstcsvtemplate: str
        the filename of the rst template for each section
        
    Notes
    -----
    Only set create_rst to True when overriding linking to custom CSV files ("_edit")
    is desired.
    """
    
    def write_section(category = None, df_settings = None):
        if category is not None:
            df_settings.to_csv(
                "settings_parsed_" + category + ".csv", quotechar="'", index=False
            )
            if create_rst:
                tmplinput = open(rstcsvtemplate)
                for tmplline in tmplinput:
                    tmplline = tmplline.replace("#SETTING#", category)
                    tmplline = tmplline.replace(
                        "#SETTING_HEADER#",
                        "\n" + category + "\n" + "-" * len(category),
                    )
    
                    rstfile.write(tmplline)

    if create_rst:
        rstfile = open("settings_doc.rst", "w")

    inputdata = open(inputfilename, encoding="utf-8").readlines()
    df = pd.DataFrame()

    settingvar_empty = dict()
    settingvar_empty["Setting"] = ""
    settingvar_empty["Unit"] = ""
    settingvar_empty["Type"] = ""
    settingvar_empty["Default"] = ""
    settingvar_empty["Scope"] = ""
    settingvar_empty["Description"] = ""
    settingvar_empty["Annotations"] = ""
    settingvar = settingvar_empty.copy()
    category = None
    
    for line in inputdata:
        if line.startswith("["):
            write_section(category = category, df_settings = df)
            # init new section:
            category = line[1 : (line.index("]"))]
            df = pd.DataFrame()

        if line.startswith("#"):
            settingvar["Annotations"] = (
                settingvar["Annotations"]
                + ("\n\r" if len(settingvar["Annotations"]) > 0 else "")
                + line[2:-1]
            )

        elif "=" in line:
            settingvar["Setting"] = line[0 : (line.index("=") - 1)]
            settingvar["Default"] = line[(line.index("=") + 1) : -1]
            df = pd.concat([df, pd.DataFrame(settingvar, index=[0])])
            # next setting:
            settingvar = settingvar_empty.copy()
    write_section(category = category, df_settings = df)
    if create_rst:
        rstfile.close()


def convert_csv():
    """
    Converts LF (after storing in LibreCalc) to LF CR again
    """
    for _root, _dirs, files in sorted(os.walk(pathlib.Path("./"))):
        for file in files:
            if "_edit." in file:
                edit2 = open(file.replace("edit", "edit2"), "wb")
                lines = open(file, "rb")
                for line in lines.readlines():
                    # check if byte before last one is not carriage return (CR)
                    if 13 != line[-2]:
                        line = line.replace(b"\n", b"\n\r")
                    edit2.write(line)
                edit2.close()


if __name__ == "__main__":
    # 1. (set create_rst = True only the first time)
    create_doc(create_rst = False)
    
    # 2. Manually edit CSV files and rename to *_edit.csv!
    # 3. Change linked CSV files in settings_doc.rst accordingly!
    
    # 4.
    #convert_csv()
