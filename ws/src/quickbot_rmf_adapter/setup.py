from setuptools import find_packages, setup

package_name = "quickbot_rmf_adapter"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Bobby Larson",
    maintainer_email="bobby@mindhive.tech",
    description="Single-robot Open-RMF fleet adapter for QuickBot.",
    license="Apache-2.0",
    entry_points={"console_scripts": []},
)
