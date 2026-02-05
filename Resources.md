Fieldworks A user0facing GUI tool for managing Lexicons (Calls C# liblcm Internally)
    D:\Github\Fieldworks
    https://github.com/sillsdev/FieldWorks/
LibLCM: the internal data model an API governing all operations on a Fieldwords Database. 
    D:\Github\liblcm
    https://github.com/sillsdev/liblcm 
FlexLibs (stable) A shallow and partial Ironpython wrapper that calls some liblcm functions to read and manipulate Flex Lexicons. 
    D:\Github\flexlibs
    https://github.com/cdfarrow/flexlibs/
FlexLibs 2.0 A deep and nearly-complete but untested Ironpython wrapper that wraps nearly all liblcm functions to read and manipulate Flex Lexicons. 
    D:\Github\flexlibs2
    https://github.com/mattgyverlee/flexlibs/
FlexTools: A Gui application for running prepared "macros" written in python. The python "macros" call FlexLibs if the function has been ported but must call liblcm directly in most cases.
    D:\Github\FlexTools
    https://github.com/cdfarrow/flextools/
FLExTools-Generator: Existing work extracting information about the LibLCM and FlexLibs codebases (for reference).
    D:\Github\FLExTools-Generator

 So FLextools is a linguist-friendly option used to run bulk changes on a Lexicon. 

 1. Flextools runs Ironpython scripts that call FlexLibs functions. 
 2. FlexLibs functions are wrappers that call LibLCM (c# and object-oriented). LibLCM retrieves or changes the data in a lexicon.  The Fieldworks reads that database and shows the updated lexicon.