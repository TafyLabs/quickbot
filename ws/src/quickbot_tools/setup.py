from setuptools import find_packages, setup

package_name = "quickbot_tools"

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
    description="QuickBot validation and operator tooling.",
    license="MIT",
    entry_points={"console_scripts": []},
)
