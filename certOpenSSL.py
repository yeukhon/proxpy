import os
import subprocess

class Cert:
    @staticmethod
    def create(commonName = 'proxpy', filename = '/tmp/proxpy.pem'):
        """
        create a new certificate signed by our CA
        """
        # if it's already been created return it without generating another one
        if os.path.exists(filename+'.pem'):
            return 0
        
        pathToCertCA = os.getcwd() + '/cert/'

        config = """
        dir		= %s			  # Where everything is kept
        ####################################################################
        [ ca ]
        default_ca	= CA_default		  # The default ca section
        
        ####################################################################
        [ CA_default ]

        certs		= $dir			  # Where the issued certs are kept
        crl_dir		= $dir			  # Where the issued crl are kept
        database	= $dir/index.txt
        new_certs_dir	= $dir			  # default place for new certs.

        certificate	= $dir/proxpyca.crt 	  # The CA certificate
        serial		= $dir/serial 		  # The current serial number
        crlnumber	= $dir/crlnumber	  # the current crl number

        crl		= $dir/proxpy.pem	  # The current CRL
        private_key	= $dir/proxpy.key	  # The private key
        RANDFILE	= $dir/.rand		  # private random number file

        name_opt 	= ca_default		  # Subject Name options
        cert_opt 	= ca_default		  # Certificate field options

        default_days	= 365			  # how long to certify for
        default_md	= sha1			  # use public key default MD
        preserve	= no			  # keep passed DN ordering

        policy		= policy_match

        # For the CA policy
        [ policy_match ]
        countryName		= match
        organizationName	= supplied
        organizationalUnitName	= supplied
        commonName		= supplied

        ####################################################################

        [ req ]
            default_bits           = 1024
            distinguished_name     = req_distinguished_name
            prompt                 = no
        [ req_distinguished_name ]
            C                      = IT
            CN                     = %s
            O                      = proxpy
            OU                     = proxpy

        [ v3_ca ] 
        basicConstraints = CA:TRUE 
        subjectKeyIdentifier = hash 
        authorityKeyIdentifier = keyid:always,issuer:always 

        """ % (pathToCertCA, commonName)

        confPath = filename+'.cnf'
        f = open(confPath, 'wb')
        f.write(config)
        f.close()

        fdnull = open(os.devnull)
        cmdCertRequest = "openssl req -config %s -nodes -new -keyout %s.key -out %s.csr" % (confPath, filename, filename)
        cmdCertSigned  = "openssl ca -batch -notext -config %s -out %s.crt -infiles %s.csr" % (confPath, filename, filename)
        p = subprocess.Popen(cmdCertRequest, shell = True, stdout = fdnull, stderr = fdnull)
        p.communicate()
        if not(p.returncode):
            p = subprocess.Popen(cmdCertSigned, shell = True, stdout = fdnull, stderr = fdnull)
            p.communicate()
            fcrt = open(filename+'.crt', 'r')
            fkey = open(filename+'.key', 'r')
            fpem = open(filename+'.pem', 'wb')
            fpem.write(fkey.read()+fcrt.read())
            fcrt.close()
            fkey.close()
            fpem.close()
        else:
            fdnull.close()
            return p.returncode

        fdnull.close()

        return p.returncode

if __name__ == "__main__":
    print Cert.create('asd', '/tmp/test')
