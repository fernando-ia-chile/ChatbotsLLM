import chromadb

client = chromadb.Client()

collection = client.create_collection("all-my-documents")

collection.add(
    documents=[
       "La empresa Fhirsaludnet se dedica a ofrecer servícios y asesoría a empresas sobre informática corporativa como software de gestión, CRMs, ERPs, portales corporativos, eCommerce, formación, DevOps, etc.",
        "En Fhirsaludnet podemos ayudarte ha mejorar tus procesos de CI/CD con nuestros productos y servícios de DevOps.",
        "En Fhirsaludnet podemos ayudarte a digitalizarte con nuestros servícios de desarrollo de aplicaciones corporativas.",
        "En Fhirsaludnet te podemos entrenar y formar a múltiples áreas de la informática corporativa como desarrollo, Data, IA o DevOps.",
        "En Fhirsaludnet te podemos desarrollar una tienda online para vender por todo el mundo y mas allà.",
        "En Fhirsaludnet te podemos asesorar en interoperabilidad en HL7 FHIR para mejorar la comunicación en la salud por todo el mundo y mas allà",
    ],
    ids=["id1", "id2","id3", "id4","id5", "id6"]
)

results = collection.query(
    query_texts=["necesito formación"], 
    n_results=2 
)

print(results)
