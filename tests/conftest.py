#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright 2020 Char Aznable <aznable.char.0083@gmail.com>
# Description: Utilities for pretty-printing Kokkos::View
#
# Distributed under terms of the 3-clause BSD license.
import re
import subprocess
import pytest
import textwrap

@pytest.fixture(scope="module")
def writeCPP(tmpdir_factory, request):
    """Write a c++ source file for gdb to examine the Kokkos::View

    Args:
        tmpdir_factory (TempdirFactory): pytest fixture for generating a
        temporary directory and file

    Returns: TODO

    """
    shape = getattr(request.module, "shape", (3,4,5))
    layout = getattr(request.module, "layout", "Kokkos::LayoutRight")
    cpp = getattr(request.module, "cpp", "")
    fnShape = "-".join(map(str, shape))
    fnLayout = re.sub(r"::", "", layout)
    p = tmpdir_factory.mktemp(f"TestView{fnLayout}{fnShape}")
    fCXX = p.join("test.cpp")
    fCXX.write(textwrap.dedent(cpp))
    yield (p, fCXX)


@pytest.fixture(scope="module")
def generateCMakeProject(writeCPP):
    p, _ = writeCPP
    fCMakeLists = p.join("CMakeLists.txt")
    fCMakeLists.write(textwrap.dedent(
        """
        cmake_minimum_required(VERSION 3.14)
        project(testLayoutRight CXX)
        include(FetchContent)

        FetchContent_Declare(
          kokkos
          GIT_REPOSITORY https://github.com/kokkos/kokkos.git
          GIT_TAG        origin/develop
          GIT_SHALLOW 1
          GIT_PROGRESS ON
        )

        FetchContent_MakeAvailable(kokkos)

        aux_source_directory(${CMAKE_CURRENT_LIST_DIR} testSources)

        foreach(testSource ${testSources})
          get_filename_component(testBinary ${testSource} NAME_WE)
          add_executable(${testBinary} ${testSource})
          target_include_directories(${testBinary} PRIVATE ${CMAKE_CURRENT_LIST_DIR})
          target_link_libraries(${testBinary} kokkos)
          add_test(NAME ${testBinary} COMMAND ${testBinary})
        endforeach()
        """
        ))
    fBuildDir = p.mkdir("build")
    with fBuildDir.as_cwd():
        cmdCmake = [f"cmake {fCMakeLists.dirpath().strpath} "
                    f"-DCMAKE_CXX_COMPILER=x86_64-conda-linux-gnu-g++ "
                    f"-DCMAKE_CXX_STANDARD=14 "
                    f"-DCMAKE_CXX_FLAGS='-DDEBUG -O0 -g' "
                    f"-DCMAKE_VERBOSE_MAKEFILE=ON "
                    ]
        rCmake = subprocess.run(cmdCmake, shell=True, capture_output=True,
                                encoding='utf-8')
        assert rCmake.returncode == 0, f"Error with running cmake: {rCmake.stderr}"
        cmdMake = [f"make -j"]
        rMake = subprocess.run(cmdMake, shell=True, capture_output=True,
                               encoding='utf-8')
        assert rMake.returncode == 0, f"Error with running make: {rMake.stderr}"
    fTest = fBuildDir.join("test")
    yield (p, fBuildDir, fTest)


@pytest.fixture
def runGDB():
    def _runGDB(content : str, fPath, executable : str):
        fPath.write(textwrap.dedent(content))
        cmd = [f"gdb -batch "
               f"{executable} "
               f"-x {fPath.realpath().strpath}"
               ]
        r = subprocess.run(cmd,
                           shell=True,
                           capture_output=True,
                           encoding='utf-8'
                           )
        assert r.returncode == 0,f"GDB error: {r.stderr}"
        # Get the output from GDB since the last breakpoint mark
        return (r,
                re.compile(r"\s*\d+\s*breakpoint\(\)\s*;\s*\n").split(r.stdout)[1].strip())
    return _runGDB

