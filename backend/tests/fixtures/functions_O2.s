	.def	@feat.00;
	.scl	3;
	.type	0;
	.endef
	.globl	@feat.00
@feat.00 = 0
	.intel_syntax noprefix
	.file	"input.c"
	.def	sum_of_squares;
	.scl	2;
	.type	32;
	.endef
	.text
	.globl	sum_of_squares                  # -- Begin function sum_of_squares
	.p2align	4
sum_of_squares:                         # @sum_of_squares
.Lfunc_begin0:
	.cv_func_id 0
# %bb.0:
	.cv_file	1 ".\\input.c" "95BAD0D43FE4029491357209ADD3EB89" 1
	.cv_inline_site_id 1 within 0 inlined_at 1 7 0
	.cv_loc	1 1 3 0                         # input.c:3:0
                                        # kill: def $edx killed $edx def $rdx
                                        # kill: def $ecx killed $ecx def $rcx
	imul	ecx, ecx
.Ltmp0:
	.cv_inline_site_id 2 within 0 inlined_at 1 7 0
	.cv_loc	2 1 3 0                         # input.c:3:0
	imul	edx, edx
.Ltmp1:
	.cv_loc	0 1 7 0                         # input.c:7:0
	lea	eax, [rdx + rcx]
	ret
.Ltmp2:
.Lfunc_end0:
                                        # -- End function
	.def	main;
	.scl	2;
	.type	32;
	.endef
	.globl	main                            # -- Begin function main
	.p2align	4
main:                                   # @main
.Lfunc_begin1:
	.cv_func_id 3
# %bb.0:
	.cv_loc	3 1 11 0                        # input.c:11:0
	mov	eax, 25
	ret
.Ltmp3:
.Lfunc_end1:
                                        # -- End function
	.section	.debug$S,"dr"
	.p2align	2, 0x0
	.long	4                               # Debug section magic
	.long	241
	.long	.Ltmp5-.Ltmp4                   # Subsection size
.Ltmp4:
	.short	.Ltmp7-.Ltmp6                   # Record length
.Ltmp6:
	.short	4353                            # Record kind: S_OBJNAME
	.long	0                               # Signature
	.asciz	"out.txt"                       # Object name
	.p2align	2, 0x0
.Ltmp7:
	.short	.Ltmp9-.Ltmp8                   # Record length
.Ltmp8:
	.short	4412                            # Record kind: S_COMPILE3
	.long	0                               # Flags and language
	.short	208                             # CPUType
	.short	23                              # Frontend version
	.short	1
	.short	3
	.short	0
	.short	23013                           # Backend version
	.short	0
	.short	0
	.short	0
	.asciz	"clang version 23.1.3 (https://github.com/llvm/llvm-project 0d261d1ca552c95a8f007e061c787ac7132fbcbc)" # Null-terminated compiler version string
	.p2align	2, 0x0
.Ltmp9:
.Ltmp5:
	.p2align	2, 0x0
	.long	246                             # Inlinee lines subsection
	.long	.Ltmp11-.Ltmp10                 # Subsection size
.Ltmp10:
	.long	0                               # Inlinee lines signature

                                        # Inlined function square starts at input.c:2
	.long	4098                            # Type index of inlined function
	.cv_filechecksumoffset	1               # Offset into filechecksum table
	.long	2                               # Starting line number
.Ltmp11:
	.p2align	2, 0x0
	.long	241                             # Symbol subsection for sum_of_squares
	.long	.Ltmp13-.Ltmp12                 # Subsection size
.Ltmp12:
	.short	.Ltmp15-.Ltmp14                 # Record length
.Ltmp14:
	.short	4423                            # Record kind: S_GPROC32_ID
	.long	0                               # PtrParent
	.long	0                               # PtrEnd
	.long	0                               # PtrNext
	.long	.Lfunc_end0-sum_of_squares      # Code size
	.long	0                               # Offset after prologue
	.long	0                               # Offset before epilogue
	.long	4101                            # Function type index
	.secrel32	sum_of_squares          # Function section relative address
	.secidx	sum_of_squares                  # Function section index
	.byte	128                             # Flags
	.asciz	"sum_of_squares"                # Function name
	.p2align	2, 0x0
.Ltmp15:
	.short	.Ltmp17-.Ltmp16                 # Record length
.Ltmp16:
	.short	4114                            # Record kind: S_FRAMEPROC
	.long	0                               # FrameSize
	.long	0                               # Padding
	.long	0                               # Offset of padding
	.long	0                               # Bytes of callee saved registers
	.long	0                               # Exception handler offset
	.short	0                               # Exception handler section
	.long	1056768                         # Flags (defines frame register)
	.p2align	2, 0x0
.Ltmp17:
	.short	.Ltmp19-.Ltmp18                 # Record length
.Ltmp18:
	.short	4456                            # Record kind: S_INLINEES
	.long	1                               # Count
	.long	4098                            # Inlinee
	.p2align	2, 0x0
.Ltmp19:
	.short	.Ltmp21-.Ltmp20                 # Record length
.Ltmp20:
	.short	4429                            # Record kind: S_INLINESITE
	.long	0                               # PtrParent
	.long	0                               # PtrEnd
	.long	4098                            # Inlinee type index
	.cv_inline_linetable	1 1 2 .Lfunc_begin0 .Lfunc_end0
	.p2align	2, 0x0
.Ltmp21:
	.short	2                               # Record length
	.short	4430                            # Record kind: S_INLINESITE_END
	.short	.Ltmp23-.Ltmp22                 # Record length
.Ltmp22:
	.short	4429                            # Record kind: S_INLINESITE
	.long	0                               # PtrParent
	.long	0                               # PtrEnd
	.long	4098                            # Inlinee type index
	.cv_inline_linetable	2 1 2 .Lfunc_begin0 .Lfunc_end0
	.p2align	2, 0x0
.Ltmp23:
	.short	2                               # Record length
	.short	4430                            # Record kind: S_INLINESITE_END
	.short	2                               # Record length
	.short	4431                            # Record kind: S_PROC_ID_END
.Ltmp13:
	.p2align	2, 0x0
	.cv_linetable	0, sum_of_squares, .Lfunc_end0
	.long	241                             # Symbol subsection for main
	.long	.Ltmp25-.Ltmp24                 # Subsection size
.Ltmp24:
	.short	.Ltmp27-.Ltmp26                 # Record length
.Ltmp26:
	.short	4423                            # Record kind: S_GPROC32_ID
	.long	0                               # PtrParent
	.long	0                               # PtrEnd
	.long	0                               # PtrNext
	.long	.Lfunc_end1-main                # Code size
	.long	0                               # Offset after prologue
	.long	0                               # Offset before epilogue
	.long	4104                            # Function type index
	.secrel32	main                    # Function section relative address
	.secidx	main                            # Function section index
	.byte	128                             # Flags
	.asciz	"main"                          # Function name
	.p2align	2, 0x0
.Ltmp27:
	.short	.Ltmp29-.Ltmp28                 # Record length
.Ltmp28:
	.short	4114                            # Record kind: S_FRAMEPROC
	.long	0                               # FrameSize
	.long	0                               # Padding
	.long	0                               # Offset of padding
	.long	0                               # Bytes of callee saved registers
	.long	0                               # Exception handler offset
	.short	0                               # Exception handler section
	.long	1056768                         # Flags (defines frame register)
	.p2align	2, 0x0
.Ltmp29:
	.short	2                               # Record length
	.short	4431                            # Record kind: S_PROC_ID_END
.Ltmp25:
	.p2align	2, 0x0
	.cv_linetable	3, main, .Lfunc_end1
	.cv_filechecksums                       # File index to string table offset subsection
	.cv_stringtable                         # String table
	.long	241
	.long	.Ltmp31-.Ltmp30                 # Subsection size
.Ltmp30:
	.short	.Ltmp33-.Ltmp32                 # Record length
.Ltmp32:
	.short	4428                            # Record kind: S_BUILDINFO
	.long	4110                            # LF_BUILDINFO index
	.p2align	2, 0x0
.Ltmp33:
.Ltmp31:
	.p2align	2, 0x0
	.section	.debug$T,"dr"
	.p2align	2, 0x0
	.long	4                               # Debug section magic
	# ArgList (0x1000)
	.short	0xa                             # Record length
	.short	0x1201                          # Record kind: LF_ARGLIST
	.long	0x1                             # NumArgs
	.long	0x74                            # Argument: int
	# Procedure (0x1001)
	.short	0xe                             # Record length
	.short	0x1008                          # Record kind: LF_PROCEDURE
	.long	0x74                            # ReturnType: int
	.byte	0x0                             # CallingConvention: NearC
	.byte	0x0                             # FunctionOptions
	.short	0x1                             # NumParameters
	.long	0x1000                          # ArgListType: (int)
	# FuncId (0x1002)
	.short	0x12                            # Record length
	.short	0x1601                          # Record kind: LF_FUNC_ID
	.long	0x0                             # ParentScope
	.long	0x1001                          # FunctionType: int (int)
	.asciz	"square"                        # Name
	.byte	241
	# ArgList (0x1003)
	.short	0xe                             # Record length
	.short	0x1201                          # Record kind: LF_ARGLIST
	.long	0x2                             # NumArgs
	.long	0x74                            # Argument: int
	.long	0x74                            # Argument: int
	# Procedure (0x1004)
	.short	0xe                             # Record length
	.short	0x1008                          # Record kind: LF_PROCEDURE
	.long	0x74                            # ReturnType: int
	.byte	0x0                             # CallingConvention: NearC
	.byte	0x0                             # FunctionOptions
	.short	0x2                             # NumParameters
	.long	0x1003                          # ArgListType: (int, int)
	# FuncId (0x1005)
	.short	0x1a                            # Record length
	.short	0x1601                          # Record kind: LF_FUNC_ID
	.long	0x0                             # ParentScope
	.long	0x1004                          # FunctionType: int (int, int)
	.asciz	"sum_of_squares"                # Name
	.byte	241
	# ArgList (0x1006)
	.short	0x6                             # Record length
	.short	0x1201                          # Record kind: LF_ARGLIST
	.long	0x0                             # NumArgs
	# Procedure (0x1007)
	.short	0xe                             # Record length
	.short	0x1008                          # Record kind: LF_PROCEDURE
	.long	0x74                            # ReturnType: int
	.byte	0x0                             # CallingConvention: NearC
	.byte	0x0                             # FunctionOptions
	.short	0x0                             # NumParameters
	.long	0x1006                          # ArgListType: ()
	# FuncId (0x1008)
	.short	0x12                            # Record length
	.short	0x1601                          # Record kind: LF_FUNC_ID
	.long	0x0                             # ParentScope
	.long	0x1007                          # FunctionType: int ()
	.asciz	"main"                          # Name
	.byte	243
	.byte	242
	.byte	241
	# StringId (0x1009)
	.short	0xa                             # Record length
	.short	0x1605                          # Record kind: LF_STRING_ID
	.long	0x0                             # Id
	.asciz	"."                             # StringData
	.byte	242
	.byte	241
	# StringId (0x100A)
	.short	0xe                             # Record length
	.short	0x1605                          # Record kind: LF_STRING_ID
	.long	0x0                             # Id
	.asciz	"input.c"                       # StringData
	# StringId (0x100B)
	.short	0xa                             # Record length
	.short	0x1605                          # Record kind: LF_STRING_ID
	.long	0x0                             # Id
	.byte	0                               # StringData
	.byte	243
	.byte	242
	.byte	241
	# StringId (0x100C)
	.short	0x46                            # Record length
	.short	0x1605                          # Record kind: LF_STRING_ID
	.long	0x0                             # Id
	.asciz	"D:\\tools\\clang+llvm-23.1.3-x86_64-pc-windows-msvc\\bin\\clang.exe" # StringData
	# StringId (0x100D)
	.short	0x73a                           # Record length
	.short	0x1605                          # Record kind: LF_STRING_ID
	.long	0x0                             # Id
	.asciz	"\"-cc1\" \"-triple\" \"x86_64-pc-windows-msvc19.51.36248\" \"-O2\" \"-S\" \"-disable-free\" \"-clear-ast-before-backend\" \"-disable-llvm-verifier\" \"-discard-value-names\" \"-mrelocation-model\" \"pic\" \"-pic-level\" \"2\" \"-mframe-pointer=none\" \"-relaxed-aliasing\" \"-fmath-errno\" \"-ffp-contract=on\" \"-fno-rounding-math\" \"-mconstructor-aliases\" \"-fms-volatile\" \"-funwind-tables=2\" \"-target-cpu\" \"x86-64\" \"-mllvm\" \"-x86-asm-syntax=intel\" \"-inline-asm=intel\" \"-tune-cpu\" \"generic\" \"-gno-column-info\" \"-gcodeview\" \"-debug-info-kind=line-tables-only\" \"-fdebug-compilation-dir=.\" \"-fcoverage-compilation-dir=.\" \"-resource-dir\" \"D:\\\\tools\\\\clang+llvm-23.1.3-x86_64-pc-windows-msvc\\\\lib\\\\clang\\\\23\" \"-internal-isystem\" \"D:\\\\tools\\\\clang+llvm-23.1.3-x86_64-pc-windows-msvc\\\\lib\\\\clang\\\\23\\\\include\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Microsoft Visual Studio\\\\18\\\\BuildTools\\\\VC\\\\Tools\\\\MSVC\\\\14.51.36231\\\\include\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Microsoft Visual Studio\\\\18\\\\BuildTools\\\\VC\\\\Tools\\\\MSVC\\\\14.51.36231\\\\atlmfc\\\\include\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Windows Kits\\\\10\\\\Include\\\\10.0.26100.0\\\\ucrt\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Windows Kits\\\\10\\\\Include\\\\10.0.26100.0\\\\shared\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Windows Kits\\\\10\\\\Include\\\\10.0.26100.0\\\\um\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Windows Kits\\\\10\\\\Include\\\\10.0.26100.0\\\\winrt\" \"-internal-isystem\" \"C:\\\\Program Files (x86)\\\\Windows Kits\\\\10\\\\Include\\\\10.0.26100.0\\\\cppwinrt\" \"-std=c17\" \"-ferror-limit\" \"19\" \"-fno-use-cxa-atexit\" \"-fms-extensions\" \"-fms-compatibility\" \"-fwrapv\" \"-fms-compatibility-version=19.51.36248\" \"-fskip-odr-check-in-gmf\" \"-fdelayed-template-parsing\" \"-fno-caret-diagnostics\" \"-fdiagnostics-show-category\" \"name\" \"-fno-color-diagnostics\" \"-vectorize-loops\" \"-vectorize-slp\" \"-faddrsig\" \"-x\" \"c\"" # StringData
	.byte	243
	.byte	242
	.byte	241
	# BuildInfo (0x100E)
	.short	0x1a                            # Record length
	.short	0x1603                          # Record kind: LF_BUILDINFO
	.short	0x5                             # NumArgs
	.long	0x1009                          # Argument: .
	.long	0x100c                          # Argument: D:\tools\clang+llvm-23.1.3-x86_64-pc-windows-msvc\bin\clang.exe
	.long	0x100a                          # Argument: input.c
	.long	0x100b                          # Argument
	.long	0x100d                          # Argument: "-cc1" "-triple" "x86_64-pc-windows-msvc19.51.36248" "-O2" "-S" "-disable-free" "-clear-ast-before-backend" "-disable-llvm-verifier" "-discard-value-names" "-mrelocation-model" "pic" "-pic-level" "2" "-mframe-pointer=none" "-relaxed-aliasing" "-fmath-errno" "-ffp-contract=on" "-fno-rounding-math" "-mconstructor-aliases" "-fms-volatile" "-funwind-tables=2" "-target-cpu" "x86-64" "-mllvm" "-x86-asm-syntax=intel" "-inline-asm=intel" "-tune-cpu" "generic" "-gno-column-info" "-gcodeview" "-debug-info-kind=line-tables-only" "-fdebug-compilation-dir=." "-fcoverage-compilation-dir=." "-resource-dir" "D:\\tools\\clang+llvm-23.1.3-x86_64-pc-windows-msvc\\lib\\clang\\23" "-internal-isystem" "D:\\tools\\clang+llvm-23.1.3-x86_64-pc-windows-msvc\\lib\\clang\\23\\include" "-internal-isystem" "C:\\Program Files (x86)\\Microsoft Visual Studio\\18\\BuildTools\\VC\\Tools\\MSVC\\14.51.36231\\include" "-internal-isystem" "C:\\Program Files (x86)\\Microsoft Visual Studio\\18\\BuildTools\\VC\\Tools\\MSVC\\14.51.36231\\atlmfc\\include" "-internal-isystem" "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\ucrt" "-internal-isystem" "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\shared" "-internal-isystem" "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\um" "-internal-isystem" "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\winrt" "-internal-isystem" "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\cppwinrt" "-std=c17" "-ferror-limit" "19" "-fno-use-cxa-atexit" "-fms-extensions" "-fms-compatibility" "-fwrapv" "-fms-compatibility-version=19.51.36248" "-fskip-odr-check-in-gmf" "-fdelayed-template-parsing" "-fno-caret-diagnostics" "-fdiagnostics-show-category" "name" "-fno-color-diagnostics" "-vectorize-loops" "-vectorize-slp" "-faddrsig" "-x" "c"
	.byte	242
	.byte	241
	.addrsig
